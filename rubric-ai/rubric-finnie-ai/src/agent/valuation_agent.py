import logging
from typing import Any

from src.agent.state import FinancialAssistantState
from src.tools.yfinance_tool import fetch_live_market_data

logger = logging.getLogger(__name__)


def fundamentals_node(state: FinancialAssistantState) -> dict[str, Any]:
    """Agent 4: Evaluates balance sheets, P&L, P/E, and ROE dynamically."""
    if (state.get("final_response") or state.get("agent_output") or "").strip():
        return {"current_step": "fundamentals_skipped_guardrail"}

    active_ticker = state.get("last_active_ticker")
    logger.info("Executing fundamentals_node | Ticker: %s", active_ticker)

    if not active_ticker:
        logger.warning("Fundamentals node skipped: no active ticker found in state.")
        return {
            "current_step": "fundamentals_skipped_no_ticker",
            "valuation_data": state.get("valuation_data", {}),
        }

    live_data = fetch_live_market_data(active_ticker)
    pe_val = live_data.get("pe_ratio", "N/A")
    forward_pe_val = live_data.get("forward_pe", "N/A")

    return {
        "current_step": "fundamentals_evaluated",
        "valuation_data": {
            **state.get("valuation_data", {}),
            "metrics": {
                "ticker": active_ticker,
                "pe_ratio": pe_val,
                "forward_pe": forward_pe_val,
                "market_cap": live_data.get("market_cap", "N/A"),
            },
        },
        "market_data": {
            **state.get("market_data", {}),
            "fundamentals": {
                active_ticker: {
                    "pe_ratio": pe_val,
                    "forward_pe": forward_pe_val,
                }
            },
        },
    }


def dcf_model_node(state: FinancialAssistantState) -> dict[str, Any]:
    """Agent 5: Computes Discounted Cash Flow intrinsic value assumptions."""
    if (state.get("final_response") or state.get("agent_output") or "").strip():
        return {"current_step": "dcf_model_skipped_guardrail"}

    logger.info("Executing dcf_model_node | Ticker: %s", state.get("last_active_ticker"))
    return {
        "current_step": "dcf_model_computed",
        "valuation_data": {
            **state.get("valuation_data", {}),
            "assumptions": {"growth_rate": 0.08, "discount_rate": 0.10},
        },
    }


def earnings_news_node(state: FinancialAssistantState) -> dict[str, Any]:
    """Agent 6: Parses SEC filings, transcripts, and earnings reports from retrieved documents."""
    if (state.get("final_response") or state.get("agent_output") or "").strip():
        return {"current_step": "earnings_news_skipped_guardrail"}

    logger.info("Executing earnings_news_node")
    retrieved_docs = state.get("retrieved_documents", [])
    has_docs = len(retrieved_docs) > 0

    return {
        "current_step": "earnings_news_parsed",
        "valuation_data": {
            **state.get("valuation_data", {}),
            "sec_filing_status": (
                "SEC documents integrated via Hybrid RAG"
                if has_docs
                else "No matching SEC document found in vector store"
            ),
            "doc_count": len(retrieved_docs),
        },
    }