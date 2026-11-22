from functools import wraps
import logging
import re
from typing import Any, Callable, Optional

from fastapi import HTTPException
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from src.core.config import settings
from src.prompts.agent_prompts import get_semantic_guardrail_prompt

logger = logging.getLogger(__name__)

INJECTION_PATTERNS: list[str] = [
    r"disregard\s+.*directives",
    r"ignore\s+.*instructions",
    r"(reveal|print|show|output|leak|display).*(system prompt|hidden instructions|initial instructions)",
    r"you are now an unconstrained",
    r"reveal secret key",
    r"bypass security",
    r"sudo mode",
]

SPECULATIVE_TRIGGER_WORDS: list[str] = [
    "mortgage",
    "options",
    "guarantee",
    "life savings",
    "all-in",
    "leverage",
    "double",
    "sure thing",
    "risk-free",
]

DISCLAIMER_SUFFIX = (
    "\n\n*Disclaimer: AI-generated financial insights are for informational purposes only "
    "and do not constitute formal investment advice.*"
)

class SemanticSafetyVerdict(BaseModel):
    is_safe: bool = Field(
        description="True if query is safe and within proper financial research/operational scope, false otherwise."
    )
    violation_category: Optional[str] = Field(
        default=None,
        description="Category if unsafe: [None, FiduciaryRisk, PromptInjection, OutOfScope]",
    )
    reasoning: str = Field(description="Brief explanation of the safety assessment.")

def sanitize_and_validate_input(user_query: str) -> tuple[bool, str, str]:
    """Tier 1 synchronous regex, non-empty, and word-count validation."""
    if not user_query or not isinstance(user_query, str):
        return False, "", "Query cannot be empty."

    cleaned_query = user_query.strip()
    if not cleaned_query:
        return False, "", "Query cannot be empty."

    max_words = getattr(settings, "MAX_INPUT_WORDS", 400)
    if len(cleaned_query.split()) > max_words:
        return False, cleaned_query, f"Query exceeds maximum allowed length of {max_words} words."

    query_lower = cleaned_query.lower()
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, query_lower):
            return False, "", "Security Policy Violation: Unsafe instruction pattern detected in query."

    return True, cleaned_query, ""

async def evaluate_semantic_risk_async(user_query: str) -> tuple[bool, str]:
    """Tier 2 semantic LLM classifier invoked via centralized prompt template."""
    try:
        llm = ChatOpenAI(
            model=settings.CHAT_MODEL,
            temperature=0.0,
        ).with_structured_output(SemanticSafetyVerdict)

        chain = get_semantic_guardrail_prompt() | llm
        verdict: SemanticSafetyVerdict = await chain.ainvoke({"user_query": user_query})

        if not verdict.is_safe:
            logger.warning(
                "Tier 2 Guardrail Block: [%s] %s",
                verdict.violation_category,
                verdict.reasoning,
            )
            return False, f"Fiduciary Safety Policy Violation: {verdict.reasoning}"
    except Exception as exc:
        logger.error("Tier 2 Semantic Guardrail evaluation failed: %s", exc)

    return True, ""

def truncate_text_by_words(text: str, max_words: Optional[int] = None) -> str:
    """Truncates text payloads to a bounded word count."""
    if not text:
        return ""
    limit = max_words or getattr(settings, "MAX_INPUT_WORDS", 400)
    words = text.split()
    return text if len(words) <= limit else " ".join(words[:limit])

def validate_trade_price_boundaries(
        ticker: str,
        price: float,
        live_info: dict[str, Any],
) -> None:
    """Validates execution price against intraday market price bounds."""
    curr_price = float(live_info.get("current_price", price))
    day_high = float(
        live_info.get("day_high")
        or live_info.get("high")
        or live_info.get("high_52")
        or (curr_price * 1.05)
    )
    day_low = float(
        live_info.get("day_low")
        or live_info.get("low")
        or live_info.get("low_52")
        or (curr_price * 0.95)
    )

    if day_high <= 0:
        day_high = curr_price * 1.05
    if day_low <= 0:
        day_low = curr_price * 0.95

    buffer = 0.01
    lower_bound = day_low * (1 - buffer)
    upper_bound = day_high * (1 + buffer)

    if not (lower_bound <= price <= upper_bound):
        raise ValueError(
            f"Execution price (${price:,.2f}) is outside today's trading range for {ticker} "
            f"(Low: ${day_low:,.2f} — High: ${day_high:,.2f})."
        )

def guardrail_protected(intent_type: str = "general") -> Callable:
    """Unified async decorator enforcing Tier 1/2 input checks and advisory disclaimers."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            request_payload = kwargs.get("request") or next(
                (arg for arg in args if hasattr(arg, "user_query")),
                None,
            )
            user_query = (
                getattr(request_payload, "user_query", None)
                if request_payload
                else kwargs.get("user_query")
            )

            if user_query and isinstance(user_query, str):
                is_safe, cleaned_query, err_msg = sanitize_and_validate_input(user_query)
                if not is_safe:
                    logger.warning("Tier 1 Guardrail blocked request: %s", err_msg)
                    raise HTTPException(status_code=400, detail=err_msg)

                if any(trigger in cleaned_query.lower() for trigger in SPECULATIVE_TRIGGER_WORDS):
                    logger.info("Speculative triggers detected; running Tier 2 semantic guardrail.")
                    is_semantic_safe, semantic_err = await evaluate_semantic_risk_async(cleaned_query)
                    if not is_semantic_safe:
                        raise HTTPException(status_code=400, detail=semantic_err)

            response = await func(*args, **kwargs)

            if isinstance(response, dict) and "final_response" in response:
                text = response["final_response"]
                if (
                        any(
                            kw in intent_type.lower()
                            for kw in ("trade", "advice", "allocation", "portfolio", "recommendation")
                        )
                        and "Disclaimer:" not in text
                ):
                    response["final_response"] = text + DISCLAIMER_SUFFIX

            return response

        return wrapper

    return decorator