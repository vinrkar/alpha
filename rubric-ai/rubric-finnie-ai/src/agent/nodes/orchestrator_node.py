import logging
import re
from typing import Any, Optional

from langchain_core.runnables import RunnableConfig

from src.agent.state import FinancialAssistantState
from src.utils.resolution import RESERVED_CONTROL_TOKENS, extract_security_identifier

logger = logging.getLogger(__name__)

VALUATION_KEYWORDS = (
    "dcf",
    "discounted cash flow",
    "fair value",
    "intrinsic",
    "sec",
    "10-q",
    "10-k",
    "balance sheet",
    "revenue",
    "growth",
    "earnings",
    "sales",
    "services",
    "margin",
    "ratio",
)
RISK_KEYWORDS = (
    "risk",
    "tax",
    "rebalance",
    "order",
    "execute",
    "drawdown",
    "sharpe",
    "compliance",
    "comply",
    "allocation",
    "limit",
)
MARKET_KEYWORDS = (
    "rsi",
    "momentum",
    "macd",
    "indicator",
    "technical",
    "portfolio",
    "holdings",
    "positions",
)
UNREALISTIC_GUARANTEE_RE = re.compile(
    r"\b(?:risk[\s-]*free|guaranteed\s+(?:return|profit|gain)|sure\s+thing|can'?t\s+lose|no\s+risk)\b",
    re.IGNORECASE,
)


def _build_unrealistic_risk_response(user_query: str, query_lower: str) -> str:
    if "mortgage" in query_lower:
        lead_msg = (
            "No mortgage, real-estate, or financial strategy is **risk-free** or a **\"sure thing\"**. "
            "Using mortgage debt or home equity introduces interest-rate, cash-flow, refinancing, and housing risks."
        )
        detail_bullets = (
            "- **Fixed Debt & Cash-Flow Pressure:** Mortgage payments remain due regardless of market moves, rate changes, or income shifts.\n"
            "- **No Guaranteed Return:** Investment or property returns are never guaranteed and can fall below borrowing costs, taxes, and fees.\n"
            "- **Housing & Collateral Risk:** Tying speculative or uncertain bets to a mortgage can jeopardize home equity or shelter."
        )
    else:
        lead_msg = "No financial or trading strategy is **risk-free** or a **\"sure thing\"**."
        detail_bullets = (
            "- **Return vs. Risk Reality:** Higher potential returns always carry market, volatility, liquidity, or counterparty risk.\n"
            "- **Leverage & Timing Risk:** Borrowed funds or short time horizons magnify losses on adverse moves.\n"
            "- **Capital Preservation:** Unhedged or concentrated bets can cause lasting capital loss."
        )

    return (
        "### ⚠️ Risk & Suitability Assessment\n\n"
        f"<strong>Query Evaluated:</strong> <em>{user_query}</em>\n\n"
        f"{lead_msg}\n\n"
        f"{detail_bullets}\n\n"
        "<strong>More Grounded Alternatives:</strong>\n"
        "- Keep dedicated cash reserves separate from investments and avoid taking on debt for speculative or promised returns.\n"
        "- Use diversified allocation, clear position sizing, and realistic long-term planning.\n\n"
        "*Disclaimer: AI-generated financial insights are for informational purposes only and do not constitute formal investment advice.*"
    )


def analyze_query_node(
        state: FinancialAssistantState,
        config: Optional[RunnableConfig] = None,
) -> dict[str, Any]:
    """Analyzes user query intent and routes execution to a target domain."""
    raw_query = (state.get("user_query") or "").strip()
    query_lower = raw_query.lower()
    holdings = state.get("portfolio_holdings", {})
    previous_ticker = state.get("last_active_ticker")
    logger.info("Analyzing query intent: '%s'", query_lower)

    if UNREALISTIC_GUARANTEE_RE.search(query_lower):
        guardrail_msg = _build_unrealistic_risk_response(raw_query, query_lower)
        logger.info("Intercepted unrealistic guarantee/risk query for suitability response.")
        return {
            "current_step": "guardrail_suitability_assessed",
            "next_domain": "risk_domain",
            "last_active_ticker": None,
            "final_response": guardrail_msg,
            "agent_output": guardrail_msg,
            "market_data": {"should_render_chart": False},
            "full_historical_closes": {},
            "analysis_results": {
                "intent": "risk_suitability_guardrail",
                "reasoning": "Flagged unrealistic guarantee / risk-free claim",
                "query_length": len(query_lower),
            },
        }

    extracted_ticker, _ = extract_security_identifier(raw_query, holdings)
    resolved_ticker = (
        extracted_ticker.upper().strip()
        if extracted_ticker and extracted_ticker.upper().strip() not in RESERVED_CONTROL_TOKENS
        else previous_ticker
    )

    if any(kw in query_lower for kw in VALUATION_KEYWORDS):
        target_domain, reasoning = "valuation_domain", "Matched valuation and financial performance keywords"
    elif any(kw in query_lower for kw in RISK_KEYWORDS):
        target_domain, reasoning = "risk_domain", "Matched risk and compliance keywords"
    elif any(kw in query_lower for kw in MARKET_KEYWORDS):
        target_domain, reasoning = "market_domain", "Matched market/technical domain keywords"
    else:
        target_domain, reasoning = "market_domain", "Default market domain routing"

    ticker_changed = bool(resolved_ticker and resolved_ticker != previous_ticker)
    clear_market_state = ticker_changed or target_domain in {"valuation_domain", "risk_domain"}

    logger.info("Routed query to %s (%s) | Active Ticker: %s", target_domain, reasoning, resolved_ticker)
    update: dict[str, Any] = {
        "current_step": "query_analyzed",
        "next_domain": target_domain,
        "last_active_ticker": resolved_ticker,
        "analysis_results": {
            "intent": target_domain,
            "reasoning": reasoning,
            "query_length": len(query_lower),
        },
    }
    if clear_market_state:
        update["full_historical_closes"] = {}
        update["market_data"] = {
            "ticker": resolved_ticker,
            "should_render_chart": False,
        }

    return update


def route_intent(state: FinancialAssistantState) -> str:
    """Conditional edge router evaluating the active domain."""
    return state.get("next_domain", "market_domain")


def should_continue_market(state: FinancialAssistantState) -> str:
    """Conditional edge controller for market domain execution flow."""
    return "skip_to_end" if (state.get("final_response") or state.get("agent_output")) else "continue_analysis"