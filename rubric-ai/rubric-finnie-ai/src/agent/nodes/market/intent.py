# src/agent/nodes/market/intent.py

from datetime import datetime, timedelta
import logging
import re
from typing import Any, Mapping, Optional, Sequence

from pydantic import BaseModel, Field

from src.core.llm_client import get_llm
from src.prompts.agent_prompts import get_intent_extraction_prompt

logger = logging.getLogger(__name__)

RESERVED_CONTROL_TOKENS: set[str] = {
    "VALID",
    "INVALID",
    "TRUE",
    "FALSE",
    "SUCCESS",
    "ERROR",
    "PENDING",
    "N/A",
    "NONE",
    "NULL",
    "PORTFOLIO",
    "FETCH",
    "WHAT",
    "HOW",
    "WHO",
    "WHERE",
}

STOP_WORDS: set[str] = {
    "A",
    "I",
    "AT",
    "BY",
    "IN",
    "IS",
    "IT",
    "OF",
    "ON",
    "OR",
    "TO",
    "THE",
    "AND",
    "FOR",
    "WITH",
    "THIS",
    "WHAT",
    "HOW",
    "RSI",
    "MACD",
    "TODAY",
    "PRICE",
    "PRICES",
    "FETCH",
    "GET",
    "SHOW",
    "PULL",
    "ANALYZE",
    "CHECK",
    "FIND",
    "HISTORICAL",
    "STOCK",
    "STOCKS",
    "OVER",
    "LAST",
    "YEAR",
    "YEARS",
    "MONTH",
    "MONTHS",
    "WEEK",
    "WEEKS",
    "DAY",
    "DAYS",
    "YTD",
    "ALL",
    "TIME",
    "FROM",
    "HAVE",
    "DO",
}.union(RESERVED_CONTROL_TOKENS)

PORTFOLIO_INTENT_KEYWORDS = ("portfolio", "holdings", "active holdings", "my positions")
RISK_INTENT_KEYWORDS = ("risk profile", "compliant", "compliance", "conservative")
VALUATION_INTENT_KEYWORDS = (
    "fair value",
    "intrinsic",
    "dcf",
    "valuation",
    "sec",
    "revenue",
    "margin",
    "growth",
    "earnings",
    "services",
)
TECHNICAL_INTENT_KEYWORDS = (
    "rsi",
    "momentum",
    "macd",
    "indicator",
    "moving average",
    "oscillators",
)
CONTEXT_PRONOUNS = ("it", "its", "they", "their", "this stock")

class FinancialQueryIntent(BaseModel):
    """Structured intent, entity, and date-range parameters extracted from a query."""

    ticker: Optional[str] = Field(default=None, description="Canonical 1-5 letter stock ticker symbol.")
    company_name: Optional[str] = Field(default=None, description="Full company name if identified.")
    is_valuation_query: bool = Field(
        default=False,
        description="True if asking about fair value, DCF, SEC docs, revenue, or margins.",
    )
    is_portfolio_summary_query: bool = Field(
        default=False,
        description="True if requesting overall portfolio summary or holdings overview.",
    )
    is_risk_compliance_query: bool = Field(
        default=False,
        description="True if asking about risk profile compliance or allocation limits.",
    )
    is_isin_query: bool = Field(default=False, description="True if asking about a specific ISIN security code.")
    isin_target: Optional[str] = Field(default=None, description="Extracted ISIN code if present.")
    uses_context_pronoun: bool = Field(
        default=False, description="True if query relies on prior context pronouns."
    )
    is_technical_indicator_query: bool = Field(
        default=False, description="True if asking about RSI, momentum, MACD."
    )
    should_render_chart: bool = Field(
        default=True, description="True if query warrants a price/performance chart visualization."
    )
    start_date: Optional[str] = Field(default=None, description="Start date (YYYY-MM-DD).")
    end_date: Optional[str] = Field(default=None, description="End date (YYYY-MM-DD).")
    period: Optional[str] = Field(default="1y", description="Timeframe period.")

def _extract_ticker_token(text: str, holdings: Mapping[str, Any]) -> Optional[str]:
    upper_text = text.upper()
    for holding_key in holdings.keys():
        sym = str(holding_key).upper()
        if re.search(r"\b" + re.escape(sym) + r"\b", upper_text):
            return sym

    tokens = [
        token
        for token in re.findall(r"\b[A-Z]{1,5}\b", upper_text)
        if token not in STOP_WORDS
    ]
    return tokens[0] if tokens else None

def resolve_ticker_context(
        user_query: str,
        holdings: Mapping[str, Any],
        messages: Sequence[Any],
        last_active_ticker: Optional[str],
        llm_extracted_ticker: Optional[str] = None,
) -> Optional[str]:
    """Resolves the active ticker symbol from LLM output, current query, message history, or state."""
    if llm_extracted_ticker and llm_extracted_ticker.upper().strip() not in STOP_WORDS:
        return llm_extracted_ticker.upper().strip()

    query_ticker = _extract_ticker_token(user_query, holdings)
    if query_ticker:
        return query_ticker

    for msg in reversed(messages):
        if isinstance(msg, Mapping):
            content = str(msg.get("content") or msg.get("query") or "")
        else:
            content = str(getattr(msg, "content", "") or "")
        if not content:
            continue
        hist_ticker = _extract_ticker_token(content, holdings)
        if hist_ticker:
            return hist_ticker

    if last_active_ticker and last_active_ticker.upper().strip() not in STOP_WORDS:
        return last_active_ticker.upper().strip()

    return None

def _build_fallback_intent(
        query_lower: str,
        holdings: Mapping[str, Any],
        isin_val: Optional[str],
        forced_start: Optional[str],
        forced_end: Optional[str],
) -> FinancialQueryIntent:
    is_portfolio = any(kw in query_lower for kw in PORTFOLIO_INTENT_KEYWORDS) and not any(
        str(t).lower() in query_lower for t in holdings.keys()
    )
    is_risk = any(kw in query_lower for kw in RISK_INTENT_KEYWORDS)
    is_valuation = (
            any(kw in query_lower for kw in VALUATION_INTENT_KEYWORDS) and not is_risk
    )
    is_technical = any(kw in query_lower for kw in TECHNICAL_INTENT_KEYWORDS)
    has_pronoun = any(
        re.search(r"\b" + re.escape(p) + r"\b", query_lower) for p in CONTEXT_PRONOUNS
    )

    today = datetime.now().date()
    start_val = forced_start or (today - timedelta(days=365)).strftime("%Y-%m-%d")
    end_val = forced_end or today.strftime("%Y-%m-%d")

    return FinancialQueryIntent(
        is_portfolio_summary_query=is_portfolio,
        is_risk_compliance_query=is_risk,
        is_valuation_query=is_valuation,
        is_isin_query=bool(isin_val),
        isin_target=isin_val,
        uses_context_pronoun=has_pronoun,
        is_technical_indicator_query=is_technical,
        should_render_chart=not is_technical,
        start_date=start_val,
        end_date=end_val,
    )

def extract_parameters_dynamically(
        user_query: str,
        holdings: Mapping[str, Any],
        last_active_ticker: Optional[str],
) -> FinancialQueryIntent:
    """Extracts intent flags, ticker/ISIN identifiers, and dates via structured LLM output with fallback."""
    current_date_str = datetime.now().strftime("%Y-%m-%d")
    isin_match = re.search(r"\b[A-Z]{2}[A-Z0-9]{9}[0-9]\b", user_query.upper())
    isin_val = isin_match.group(0) if isin_match else None

    query_lower = user_query.lower()
    is_portfolio = any(kw in query_lower for kw in PORTFOLIO_INTENT_KEYWORDS) and not any(
        str(t).lower() in query_lower for t in holdings.keys()
    )
    is_technical = any(kw in query_lower for kw in TECHNICAL_INTENT_KEYWORDS)

    query_dates = re.findall(r"\b\d{4}-\d{2}-\d{2}\b", user_query)
    forced_start_date = query_dates[0] if len(query_dates) >= 1 else None
    forced_end_date = query_dates[1] if len(query_dates) >= 2 else None

    try:
        llm = get_llm(temperature=0.0)
        structured_llm = llm.with_structured_output(FinancialQueryIntent)
        chain = get_intent_extraction_prompt() | structured_llm

        result = chain.invoke(
            {
                "current_date": current_date_str,
                "query": user_query,
                "holdings_keys": list(holdings.keys()),
                "last_active_ticker": last_active_ticker or "None",
            }
        )
        if result:
            if result.ticker and result.ticker.upper() in RESERVED_CONTROL_TOKENS:
                result.ticker = None
            if isin_val and not result.is_isin_query:
                result.is_isin_query = True
                result.isin_target = isin_val
            if forced_start_date:
                result.start_date = forced_start_date
            if forced_end_date:
                result.end_date = forced_end_date

            result.is_technical_indicator_query = is_technical
            if is_technical:
                result.should_render_chart = False
            if is_portfolio and result.ticker:
                result.is_portfolio_summary_query = False
            return result
    except Exception as exc:
        logger.warning("Structured LLM intent extraction failed: %s", exc)

    return _build_fallback_intent(
        query_lower=query_lower,
        holdings=holdings,
        isin_val=isin_val,
        forced_start=forced_start_date,
        forced_end=forced_end_date,
    )