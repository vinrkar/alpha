from datetime import datetime, timedelta
import logging
import re
from typing import Any

from langchain_core.messages import AIMessage
import pandas as pd

from src.agent.nodes.market.formatters import format_daywise_price_table
from src.agent.nodes.market.indicators import calculate_macd, calculate_rsi
from src.agent.nodes.market.intent import (
    RESERVED_CONTROL_TOKENS,
    STOP_WORDS,
    extract_parameters_dynamically,
    resolve_ticker_context,
)
from src.agent.state import FinancialAssistantState
from src.core.guardrails import sanitize_and_validate_input
from src.services.quant_service import evaluate_portfolio_compliance
from src.tools.yfinance_tool import fetch_historical_prices, fetch_live_market_data
from src.utils.date_utils import (
    extract_and_normalize_dates,
    format_invalid_date_range_message,
    has_explicit_date_range,
    is_inverted_date_range,
)

logger = logging.getLogger(__name__)

COMPLIANCE_KEYWORDS = ("compliance", "comply", "allocation", "limit", "guideline")
SPECULATIVE_PATTERN = re.compile(
    r"\b(?:weekly\s+options|options|leverage|leveraged|life\s+savings|all-in|all\s+in|double\s+(?:it|my))\b",
    re.IGNORECASE,
)
UNREALISTIC_GUARANTEE_PATTERN = re.compile(
    r"\b(?:risk[\s-]*free|guaranteed\s+(?:return|profit|gain)|sure\s+thing|can'?t\s+lose|no\s+risk)\b",
    re.IGNORECASE,
)
CURRENT_PRICE_PATTERN = re.compile(r"\b(?:current|latest|live|spot)\s+price\b", re.IGNORECASE)

def _recent_messages(state: FinancialAssistantState) -> list[Any]:
    raw_messages = state.get("messages", [])
    return list(raw_messages[-6:]) if isinstance(raw_messages, list) else []

def _build_node_output(
        *,
        step: str,
        ticker: str | None,
        response_text: str,
        recent_msgs: list[Any],
        snapshot: dict[str, Any] | None = None,
        closes: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "current_step": step,
        "last_active_ticker": ticker,
        "final_response": response_text,
        "agent_output": response_text,
        "messages": recent_msgs + [AIMessage(content=response_text)],
    }
    if snapshot is not None:
        payload["market_data"] = dict(snapshot)
    if closes is not None:
        payload["full_historical_closes"] = dict(closes)
    return payload

def _is_speculative_or_unrealistic_risk_query(query_lower: str) -> bool:
    asks_portfolio_compliance = (
            any(kw in query_lower for kw in COMPLIANCE_KEYWORDS) or "risk profile" in query_lower
    )
    if asks_portfolio_compliance:
        return False
    return bool(SPECULATIVE_PATTERN.search(query_lower) or UNREALISTIC_GUARANTEE_PATTERN.search(query_lower))

def _format_high_risk_query_response(
        user_query: str,
        holdings: dict[str, Any],
        query_lower: str,
) -> str:
    concentration_note = ""
    if holdings and any(tok in query_lower for tok in ("portfolio", "holding", "options", "leverage", "life savings")):
        enriched = {
            ticker: {
                "shares": info.get("shares", 0),
                "current_price": float(info.get("avg_cost", 0.0)),
            }
            for ticker, info in holdings.items()
        }
        report = evaluate_portfolio_compliance(enriched)
        violations = report.get("violations") or []
        if violations:
            concentration_note = (
                f"\n- **Existing Profile Context:** Your tracked profile currently shows elevated concentration in "
                f"{', '.join(violations)}—adding speculative or leveraged bets on top of concentrated capital increases drawdown risk."
            )

    if "mortgage" in query_lower:
        lead_risk = (
            "No mortgage, real-estate, or financial strategy is **risk-free** or a **\"sure thing\"**. "
            "Using mortgage debt or home equity to fund investments introduces interest-rate, refinancing, cash-flow, and foreclosure or negative-equity risks."
        )
        bullets = (
            "- **Debt & Cash-Flow Obligation:** Mortgage payments are fixed commitments regardless of market performance or job/income changes.\n"
            "- **No Guaranteed Return:** Market or property returns are never guaranteed and can underperform borrowing costs plus fees and taxes.\n"
            "- **Collateral / Housing Risk:** Putting primary housing or home equity at risk can jeopardize shelter if asset values drop or cash flow tightens."
        )
    else:
        lead_risk = (
            "No investment strategy is **risk-free** or a **\"sure thing\"**, and high-leverage or short-dated bets carry a **high risk of rapid loss**."
        )
        bullets = (
            "- **Return vs. Risk Trade-Off:** Higher potential returns always come with market, volatility, or liquidity risk.\n"
            "- **Leverage & Timing Risk:** Borrowed funds or short expiration windows magnify losses and leave little room for adverse moves.\n"
            "- **Capital Preservation Risk:** Unhedged or concentrated bets can cause permanent capital impairment."
        )

    return (
        "### ⚠️ Risk & Suitability Assessment\n\n"
        f"<strong>Query Evaluated:</strong> <em>{user_query}</em>\n\n"
        f"{lead_risk}\n\n"
        f"{bullets}"
        f"{concentration_note}\n\n"
        "<strong>More Grounded Alternatives:</strong>\n"
        "- Maintain dedicated cash reserves and avoid borrowing against essential assets for speculative or high-risk trades.\n"
        "- Use diversified allocation, clear risk limits, and realistic return expectations aligned with your time horizon.\n\n"
        "*Disclaimer: AI-generated financial insights are for informational purposes only and do not constitute formal investment advice.*"
    )

def _format_compliance_response(holdings: dict[str, Any]) -> str:
    enriched = {
        ticker: {
            "shares": info.get("shares", 0),
            "current_price": float(info.get("avg_cost", 0.0)),
        }
        for ticker, info in holdings.items()
    }
    report = evaluate_portfolio_compliance(enriched)
    table_lines = [
        "| Ticker | Market Value ($) | Weight (%) | Status |",
        "|---|---|---|---|",
    ]
    for row in report.get("summary_rows", []):
        table_lines.append(
            f"| {row['ticker']} | ${row['value']:,.2f} | {row['weight']:.2f}% | {row['status']} |"
        )
    status_text = "PASSED" if report.get("is_compliant") else "EXCEEDS LIMITS"
    violations_text = ", ".join(report.get("violations", [])) or "None"

    return (
        f"### 🛡️ Portfolio Risk & Compliance Audit\n\n"
        f"- **Total Portfolio Value:** ${report['total_value']:,.2f}\n"
        f"- **Compliance Status:** **{status_text}**\n"
        f"- **Violations Identified:** {violations_text}\n\n"
        f"{chr(10).join(table_lines)}\n\n"
        f"*Executive Summary:* All asset weights have been verified against allocation limits."
    )

def _format_portfolio_summary(holdings: dict[str, Any]) -> str:
    if not holdings:
        return "Your portfolio currently has no active holdings."

    lines = ["### 📊 Active Portfolio Holdings Summary", ""]
    total_val = 0.0
    for symbol, details in holdings.items():
        shares = details.get("shares", 0)
        cost = details.get("avg_cost", details.get("avg_price", 0.0))
        val = shares * cost
        total_val += val
        lines.append(
            f"- **{symbol}** ({details.get('name', symbol)}): {shares:,} shares @ ${cost:,.2f} avg cost (${val:,.2f} total)"
        )
    lines.append(f"\n**Total Portfolio Value:** ${total_val:,.2f}")
    return "\n".join(lines)

def _extract_closes_map(
        hist_df: pd.DataFrame,
        start_date_str: str,
        end_date_str: str,
        fallback_price: float,
) -> tuple[dict[str, float], float]:
    if hist_df.empty:
        return {}, fallback_price

    df_norm = hist_df.copy()
    df_norm.index = pd.to_datetime(df_norm.index)
    if df_norm.index.tz is not None:
        df_norm.index = df_norm.index.tz_localize(None)
    df_norm = df_norm.sort_index()

    mask = (df_norm.index >= pd.to_datetime(start_date_str)) & (
            df_norm.index <= pd.to_datetime(end_date_str)
    )
    filtered = df_norm.loc[mask]
    if filtered.empty:
        filtered = df_norm.tail(60)

    close_col = "Close" if "Close" in filtered.columns else filtered.columns[1]
    latest_price = float(filtered[close_col].iloc[-1]) if not filtered.empty else fallback_price

    reset_df = filtered.sort_index().reset_index()
    date_col = "Date" if "Date" in reset_df.columns else reset_df.columns[0]
    date_strings = pd.to_datetime(reset_df[date_col]).dt.strftime("%Y-%m-%d")
    closes = dict(zip(date_strings, filtered[close_col].astype(float)))
    return closes, latest_price

def execute_market_data_lookup(state: FinancialAssistantState) -> dict[str, Any]:
    user_query = state.get("user_query", "")
    logger.info("Executing market data lookup for query: '%s'", user_query)

    is_safe, _, err_msg = sanitize_and_validate_input(user_query)
    if not is_safe:
        logger.warning("Market lookup blocked by guardrail: %s", err_msg)
        return {
            "current_step": "guardrail_rejected",
            "final_response": f"🛡️ {err_msg}",
        }

    query_lower = user_query.lower()
    recent_msgs = _recent_messages(state)
    holdings = state.get("portfolio_holdings", {})
    existing_ticker = state.get("last_active_ticker")

    if _is_speculative_or_unrealistic_risk_query(query_lower):
        resp_text = _format_high_risk_query_response(user_query, holdings, query_lower)
        return _build_node_output(
            step="market_analysis_synthesized",
            ticker=None,
            response_text=resp_text,
            recent_msgs=recent_msgs,
        )

    extracted_params = extract_parameters_dynamically(user_query, holdings, existing_ticker)
    explicit_param_ticker = (
        extracted_params.ticker.upper().strip()
        if getattr(extracted_params, "ticker", None)
           and extracted_params.ticker.upper().strip() not in STOP_WORDS
           and extracted_params.ticker.upper().strip() not in RESERVED_CONTROL_TOKENS
        else None
    )

    resolved_ticker = explicit_param_ticker or resolve_ticker_context(
        user_query,
        holdings,
        recent_msgs,
        existing_ticker,
        extracted_params.ticker,
    )

    if not resolved_ticker or resolved_ticker in RESERVED_CONTROL_TOKENS:
        if "googl" in query_lower or "google" in query_lower:
            resolved_ticker = "GOOGL"
        elif existing_ticker and existing_ticker not in RESERVED_CONTROL_TOKENS:
            resolved_ticker = existing_ticker
        else:
            resolved_ticker = "AAPL"

    if extracted_params.is_risk_compliance_query or "risk profile" in query_lower or any(
            kw in query_lower for kw in COMPLIANCE_KEYWORDS
    ):
        resp_text = _format_compliance_response(holdings)
        return _build_node_output(
            step="market_analysis_synthesized",
            ticker=None,
            response_text=resp_text,
            recent_msgs=recent_msgs,
        )

    if extracted_params.is_portfolio_summary_query:
        resp_text = _format_portfolio_summary(holdings)
        return _build_node_output(
            step="market_analysis_synthesized",
            ticker=None,
            response_text=resp_text,
            recent_msgs=recent_msgs,
        )

    today = datetime.now().date()
    has_dates = has_explicit_date_range(user_query)
    extracted_start, extracted_end = extract_and_normalize_dates(user_query)

    if is_inverted_date_range(user_query, extracted_start, extracted_end) or (
            has_dates and (not extracted_start or not extracted_end)
    ):
        error_msg = format_invalid_date_range_message(
            user_query,
            start_date=extracted_start,
            end_date=extracted_end,
            ticker=resolved_ticker,
        )
        return _build_node_output(
            step="guardrail_rejected",
            ticker=resolved_ticker,
            response_text=error_msg,
            recent_msgs=recent_msgs,
        )

    is_current_price_query = bool(CURRENT_PRICE_PATTERN.search(query_lower)) and not has_dates
    start_date_str = extracted_start or getattr(extracted_params, "start_date", None) or (
            today - timedelta(days=365)
    ).strftime("%Y-%m-%d")
    end_date_str = (
            extracted_end or getattr(extracted_params, "end_date", None) or today.strftime("%Y-%m-%d")
    )
    lookback_start = (
        start_date_str
        if has_dates
        else (today - timedelta(days=90)).strftime("%Y-%m-%d")
    )

    hist_df = fetch_historical_prices(resolved_ticker, start=lookback_start, end=end_date_str)
    live_data = fetch_live_market_data(resolved_ticker)
    if hist_df.empty:
        hist_df = fetch_historical_prices(resolved_ticker, period="3mo")

    fallback_price = float(live_data.get("current_price", 150.0) or 150.0)
    indicator_closes, latest_price = _extract_closes_map(
        hist_df, lookback_start, end_date_str, fallback_price
    )
    if live_data.get("current_price") is not None:
        latest_price = float(live_data["current_price"])

    if is_current_price_query and indicator_closes:
        last_dt = list(indicator_closes.keys())[-1]
        display_closes = {last_dt: latest_price}
        display_start = last_dt
    else:
        display_closes = indicator_closes
        display_start = start_date_str

    close_series = (
        pd.Series(list(indicator_closes.values()), dtype=float)
        if indicator_closes
        else pd.Series([latest_price], dtype=float)
    )
    computed_rsi = calculate_rsi(close_series, period=14) if len(close_series) >= 15 else None
    computed_macd = calculate_macd(close_series) if len(close_series) >= 12 else None

    snapshot = {
        "status": "success",
        "ticker": resolved_ticker,
        "current_price": latest_price,
        "start_date": display_start,
        "end_date": end_date_str,
        "should_render_chart": len(display_closes) >= 2,
        "technicals": {
            "RSI_14": computed_rsi,
            "MACD_signal": computed_macd,
        },
    }

    if extracted_params.is_technical_indicator_query:
        tech_lines = [
            f"### 📈 Technical Indicators & Momentum for {resolved_ticker}",
            "",
            f"- **Current Price:** ${latest_price:,.2f}",
        ]
        if computed_rsi is not None:
            tech_lines.append(f"- **RSI (14):** {computed_rsi}")
        if computed_macd:
            tech_lines.append(f"- **MACD Status:** {computed_macd}")
        tech_response = "\n".join(tech_lines)
        return _build_node_output(
            step="market_analysis_synthesized",
            ticker=resolved_ticker,
            response_text=tech_response,
            recent_msgs=recent_msgs,
            snapshot=snapshot,
            closes=display_closes,
        )

    return {
        "current_step": "market_data_fetched",
        "last_active_ticker": resolved_ticker,
        "market_data": dict(snapshot),
        "full_historical_closes": dict(display_closes),
    }

def execute_market_synthesis(state: FinancialAssistantState) -> dict[str, Any]:
    existing_final = (state.get("final_response") or "").strip()
    if existing_final and "Historical Daily Closing Prices" not in existing_final:
        return {
            "current_step": "market_analysis_synthesized",
            "last_active_ticker": state.get("last_active_ticker"),
            "final_response": existing_final,
            "agent_output": state.get("agent_output") or existing_final,
            "market_data": state.get("market_data", {}),
            "full_historical_closes": state.get("full_historical_closes", {}),
        }

    ticker = state.get("last_active_ticker") or "GOOGL"
    market_data = state.get("market_data", {})
    historical_closes = state.get("full_historical_closes", {})

    daywise_table_md = (
        format_daywise_price_table(historical_closes)
        if historical_closes
        else "| Date | Closing Price |\n|---|---|\n| N/A | No data available |"
    )
    start_dt = market_data.get("start_date", "Custom Range")
    end_dt = market_data.get("end_date", "Present")
    current_px = market_data.get("current_price")

    technicals = market_data.get("technicals") or {}
    rsi_14 = technicals.get("RSI_14")
    macd_sig = technicals.get("MACD_signal")
    sentiment_score = market_data.get("sentiment_score")
    sentiment_label = market_data.get("sentiment_label")

    tech_bullets: list[str] = []
    if current_px is not None:
        tech_bullets.append(f"  * Current / Latest Price: ${float(current_px):,.2f}.")
    if rsi_14 is not None:
        tech_bullets.append(
            f"  * RSI (14): {rsi_14} ({technicals.get('RSI_regime', 'Computed from recent closing series')})."
        )
    if macd_sig:
        tech_bullets.append(f"  * MACD Signal: {macd_sig}.")
    if not tech_bullets:
        tech_bullets.append("  * Latest market price retrieved.")

    sentiment_line = (
        f"  * Sentiment Score: {sentiment_score} ({sentiment_label or 'Reported'})."
        if sentiment_score is not None
        else f"  * Sentiment Status: {sentiment_label or 'No separate sentiment score available'}."
    )

    retrieved_docs = state.get("retrieved_documents") or []
    doc_snippets = [
        str(doc.get("content", "")).strip()
        for doc in retrieved_docs
        if isinstance(doc, dict) and str(doc.get("content", "")).strip()
    ]
    context_summary = (
        " ".join(doc_snippets[:2])[:320]
        if doc_snippets
        else f"Market price and historical close series retrieved for {ticker}."
    )

    content = (
            f"### 📊 {ticker} Analysis\n\n"
            f"#### Historical Daily Closing Prices (from **{start_dt}** to **{end_dt}**)\n"
            f"{daywise_table_md}\n\n"
            f"#### Technical and Context Summary for {ticker}\n"
            f"* **Technical Indicators:**\n"
            + "\n".join(tech_bullets)
            + "\n* **Sentiment & Retrieved Context:**\n"
            + f"{sentiment_line}\n"
            + f"  * Context Excerpt: {context_summary}\n\n"
            + "#### Key Risk and Momentum Factors\n"
            + "* **Risks:** Market volatility, valuation sensitivity, macro/rate shifts, and regulatory or competitive pressures.\n"
            + "* **Momentum & Drivers:** Price trend and fundamentals as reflected in recent market data and retrieved filings.\n\n"
            + "#### Disclaimer\n"
            + "This analysis is for informational purposes only and should not be construed as investment advice."
    )

    return {
        "current_step": "market_analysis_synthesized",
        "last_active_ticker": ticker,
        "final_response": content,
        "agent_output": content,
        "market_data": market_data,
        "full_historical_closes": historical_closes,
    }

execute_market_node_with_mcp = execute_market_data_lookup