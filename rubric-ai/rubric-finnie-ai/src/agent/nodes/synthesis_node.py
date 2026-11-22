import logging
import re
from typing import Any

from langchain_core.runnables import RunnableConfig

from src.agent.state import FinancialAssistantState
from src.core.llm_client import get_llm
from src.prompts.agent_prompts import get_market_analysis_prompt, get_qa_prompt
from src.tools.yfinance_tool import fetch_live_market_data
from src.utils.resolution import (
    RESERVED_CONTROL_TOKENS,
    extract_security_identifier,
    find_matching_holding,
    resolve_isin_from_ticker,
    resolve_ticker_from_isin,
)

logger = logging.getLogger(__name__)

PORTFOLIO_PHRASES = (
    "portfolio",
    "holdings",
    "active holdings",
    "my positions",
    "summary of holdings",
)
SEARCH_KEYWORDS = ("search my portfolio", "do i hold", "matching", "isin", "ticker")


def _clean_latex_delimiters(text: str) -> str:
    """Converts raw LaTeX inline/block delimiters into readable plain text for mixed HTML/Markdown cards."""
    cleaned = re.sub(r"\\\[\s*(.*?)\s*\\\]", r"\1", text, flags=re.DOTALL)
    cleaned = re.sub(r"\\\(\s*(.*?)\s*\\\)", r"\1", cleaned, flags=re.DOTALL)
    cleaned = re.sub(r"\\text\{([^}]*)\}", r"\1", cleaned)
    cleaned = cleaned.replace(r"\times", "×").replace(r"\approx", "≈").replace(r"\frac", "")
    # Remove dangling empty numbered step or bullet lines at the end of a model response
    cleaned = re.sub(r"(?m)(?:\n\s*\d+\.|\n\s*[-*])\s*$", "", cleaned).strip()
    return cleaned


def _format_holding_detail(
        symbol: str,
        holding: dict[str, Any],
        holdings: dict[str, Any],
        isin_fallback: str | None,
) -> str:
    shares = float(holding.get("shares", 0))
    avg_cost = float(holding.get("avg_cost", holding.get("avg_price", 0.0)))
    total_cost = shares * avg_cost

    live_res = fetch_live_market_data(symbol)
    curr_price = float(live_res.get("current_price", avg_cost)) if isinstance(live_res, dict) else avg_cost
    market_val = shares * curr_price
    gain_loss = market_val - total_cost

    total_port_val = sum(
        float(d.get("shares", 0)) * float(d.get("avg_cost", d.get("avg_price", 0.0)))
        for d in holdings.values()
    )
    pct_port = (market_val / total_port_val * 100) if total_port_val > 0 else 0.0
    sector = holding.get("sector", "Financial Services")
    raw_exchange = holding.get("exchange", "NYSE")
    exchange = ", ".join(str(x) for x in raw_exchange) if isinstance(raw_exchange, list) else str(raw_exchange)
    company_name = holding.get("name", symbol)
    target_isin = holding.get("isin", isin_fallback or "N/A")

    gl_prefix = "+" if gain_loss >= 0 else ""
    gl_str = f"{gl_prefix}${gain_loss:,.2f}" if gain_loss >= 0 else f"(${abs(gain_loss):,.2f})"

    return (
        f"### Portfolio Holding Inspection: {symbol}\n\n"
        f"| Metric | Details |\n"
        f"| :--- | :--- |\n"
        f"| **Ticker** | `{symbol}` |\n"
        f"| **ISIN** | `{target_isin}` |\n"
        f"| **Name** | {company_name} |\n"
        f"| **Shares** | {shares:,.4f} |\n"
        f"| **Avg Unit Price** | ${avg_cost:,.2f} |\n"
        f"| **Curr Price** | ${curr_price:,.2f} |\n"
        f"| **Cost Basis** | ${total_cost:,.2f} |\n"
        f"| **Market Val** | ${market_val:,.2f} |\n"
        f"| **% Prtf** | {pct_port:.2f}% |\n"
        f"| **G/L** | {gl_str} |\n"
        f"| **Sect** | {sector} |\n"
        f"| **Exch** | {exchange} |\n"
    )


def _format_holdings_overview(holdings: dict[str, Any]) -> str:
    if not holdings:
        return "Your portfolio currently has no active holdings."

    lines = ["### Active Portfolio Holdings Summary"]
    total_val = sum(
        float(d.get("shares", 0)) * float(d.get("avg_cost", d.get("avg_price", 0.0)))
        for d in holdings.values()
    )
    for symbol, details in holdings.items():
        shares = details.get("shares", 0)
        cost = details.get("avg_cost", details.get("avg_price", 0.0))
        lines.append(
            f"* **{symbol}** ({details.get('name', symbol)}): {shares:,} shares @ ${cost:,.2f} (${shares * cost:,.2f} total)"
        )
    if total_val > 0:
        lines.append(f"\n**Total Portfolio Value:** ${total_val:,.2f}")
    return "\n".join(lines)


def synthesize_response_node(
        state: FinancialAssistantState,
        config: RunnableConfig,
) -> dict[str, Any]:
    query = state.get("user_query", "")
    query_lower = query.lower()
    holdings = state.get("portfolio_holdings", {})
    existing_messages = list(state.get("messages", []))
    target_domain = state.get("next_domain", "market_domain")
    retrieved_docs = state.get("retrieved_documents", [])
    target_ticker = state.get("last_active_ticker")

    is_search_intent = any(kw in query_lower for kw in SEARCH_KEYWORDS)
    ticker_extracted, isin_extracted = extract_security_identifier(query, holdings)
    if ticker_extracted and ticker_extracted.upper() not in RESERVED_CONTROL_TOKENS:
        target_ticker = ticker_extracted.upper()

    if is_search_intent and (ticker_extracted or isin_extracted):
        found_symbol, found_holding = find_matching_holding(ticker_extracted, isin_extracted, holdings)
        if found_symbol and found_holding:
            final_text = _format_holding_detail(found_symbol, found_holding, holdings, isin_extracted)
            resolved_out = found_symbol
        elif isin_extracted:
            resolved_out = resolve_ticker_from_isin(isin_extracted)
            final_text = f"No security with ISIN `{isin_extracted}` ({resolved_out}) is currently present in your active portfolio holdings."
        else:
            resolved_out = ticker_extracted
            target_isin = resolve_isin_from_ticker(resolved_out) if resolved_out else "N/A"
            final_text = (
                f"No security with Ticker **{resolved_out}** (`{target_isin}`) is currently present in your active portfolio holdings."
                if resolved_out
                else "Please specify a valid stock ticker or ISIN to search in your portfolio."
            )

        return {
            "current_step": "completed",
            "final_response": final_text,
            "messages": existing_messages + [{"role": "assistant", "content": final_text}],
            "last_active_ticker": resolved_out,
            "full_historical_closes": {},
            "market_data": {"should_render_chart": False},
        }

    existing_output = (state.get("agent_output") or state.get("final_response") or "").strip()
    if existing_output and not existing_output.startswith("Please specify a stock ticker"):
        existing_market = dict(state.get("market_data", {}))
        existing_market.setdefault("should_render_chart", False)
        return {
            "current_step": "completed",
            "final_response": existing_output,
            "messages": existing_messages + [{"role": "assistant", "content": existing_output}],
            "last_active_ticker": target_ticker,
            "full_historical_closes": state.get("full_historical_closes", {}),
            "market_data": existing_market,
        }

    full_closes = state.get("full_historical_closes", {})
    market_data = dict(state.get("market_data", {}))
    if target_ticker and not market_data.get("ticker"):
        market_data["ticker"] = target_ticker

    if target_ticker == "PORTFOLIO" or any(phrase in query_lower for phrase in PORTFOLIO_PHRASES):
        overview_text = _format_holdings_overview(holdings)
        return {
            "current_step": "completed",
            "final_response": overview_text,
            "messages": existing_messages + [{"role": "assistant", "content": overview_text}],
            "last_active_ticker": None,
            "full_historical_closes": {},
            "market_data": {"should_render_chart": False},
        }

    if target_domain == "valuation_domain" or retrieved_docs:
        if not target_ticker or target_ticker in RESERVED_CONTROL_TOKENS:
            full_final_response = "Please specify a valid stock ticker or portfolio holding you would like to analyze."
        else:
            valuation_assumptions = (state.get("valuation_data") or {}).get("assumptions") or {}
            assumptions_note = (
                f"\n\nModel Assumptions: {valuation_assumptions}"
                if valuation_assumptions
                else ""
            )
            context_text = (
                "\n\n".join(doc.get("content", str(doc)) for doc in retrieved_docs)
                if retrieved_docs
                else "No specific internal RAG documents found."
            )

            formatted_assumptions = (
                "\n".join(f"- {k}: {v}" for k, v in valuation_assumptions.items())
                if valuation_assumptions
                else "None provided."
            )
            grounded_context = (
                f"{context_text}\n\n"
                f"Model Assumptions:\n{formatted_assumptions}\n\n"
                "Formatting & Grounding Rules:\n"
                "- Ground all figures strictly in the provided context and model assumptions; do not invent external rates or unstated financial figures.\n"
                "- When presenting a DCF valuation, explicitly show formulas for FCF_t (t = 1..N), PV(FCF_t) = FCF_t / (1 + discount_rate)^t, "
                "Terminal Value = FCF_N × (1 + g) / (discount_rate - g) (noting discount_rate > g), PV(TV) = Terminal Value / (1 + discount_rate)^N, and Total DCF Value.\n"
                "- Write all math in plain readable text without LaTeX \\( \\), \\[ \\], \\frac, or \\text{...} delimiters.\n"
                "- Put every numbered step and bullet item (- ) on its own line; never emit empty markers or trailing orphan lines after Conclusion."
            )
            try:
                response = (get_qa_prompt() | get_llm(temperature=0.0)).invoke(
                    {"context": grounded_context, "query": query},
                    config=config,
                )
                content = _clean_latex_delimiters(str(response.content))
            except Exception as exc:
                logger.warning("QA synthesis fallback for %s: %s", target_ticker, exc)
                content = f"Analyzed valuation and documents for {target_ticker}."
            full_final_response = f"### {target_ticker} Valuation & RAG Insights\n\n{content}"

        return {
            "current_step": "completed",
            "final_response": full_final_response,
            "messages": existing_messages + [{"role": "assistant", "content": full_final_response}],
            "last_active_ticker": target_ticker,
            "full_historical_closes": {},
            "market_data": {"ticker": target_ticker, "should_render_chart": False},
        }

    matched_ticker, _ = find_matching_holding(ticker_extracted, isin_extracted, holdings)
    target_ticker = target_ticker or matched_ticker

    if not target_ticker or target_ticker in RESERVED_CONTROL_TOKENS:
        full_final_response = "Please specify a valid stock ticker or portfolio holding you would like to analyze."
    else:
        clean_summary = {
            "ticker": target_ticker,
            "price": market_data.get("current_price", "N/A"),
            "pe_ratio": market_data.get("pe_ratio", "N/A"),
        }
        try:
            response = (get_market_analysis_prompt() | get_llm(temperature=0.0)).invoke(
                {"ticker": clean_summary["ticker"], "market_data": str(clean_summary)},
                config=config,
            )
            content = _clean_latex_delimiters(str(response.content))
        except Exception as exc:
            logger.warning("Market synthesis fallback for %s: %s", target_ticker, exc)
            content = f"Retrieved data for {target_ticker}."
        full_final_response = f"### {target_ticker} Analysis\n\n{content}"

    market_data.setdefault("should_render_chart", len(full_closes) >= 2)
    return {
        "current_step": "completed",
        "final_response": full_final_response,
        "messages": existing_messages + [{"role": "assistant", "content": full_final_response}],
        "last_active_ticker": target_ticker,
        "full_historical_closes": full_closes,
        "market_data": market_data,
    }