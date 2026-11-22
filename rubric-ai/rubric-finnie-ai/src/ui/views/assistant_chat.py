import concurrent.futures
from datetime import datetime
import logging
import re
import time
import uuid
from typing import Any, Optional

import requests
import streamlit as st

from src.agent.nodes.market.formatters import format_daywise_price_table
from src.core.guardrails import sanitize_and_validate_input
from src.core.llm_client import get_embedding
from src.core.redis_client import get_semantic_cache, set_semantic_cache
from src.services.quant_service import evaluate_portfolio_compliance
from src.tools.yfinance_tool import fetch_live_market_data
from src.ui.components.helpers import (
    _has_meaningful_query,
    add_message_to_history,
    render_clear_chat_history_button,
    render_paginated_chat_history,
    run_async,
)
from src.ui.components.styles import render_subheader_card
from src.utils.date_utils import extract_and_normalize_dates, has_date_reference

logger = logging.getLogger(__name__)

PRIVATE_QUERY_KEYWORDS = ("portfolio", "holding", "my asset", "allocation", "balance", "trade")
COMPLIANCE_KEYWORDS = ("compliance", "comply", "allocation", "limit", "guideline")
CHART_KEYWORDS = ("price", "historical", "history", "performing", "today", "chart", "trend", "stock")
PRICE_TABLE_KEYWORDS = ("price", "historical", "history", "performing", "today", "chart", "trend")
HISTORICAL_RANGE_KEYWORDS = ("historical", "history", "between", "from ", "to ", "chart", "trend")

EMPTY_CHAT_QUERY_MSG = "Please type a financial research question or ticker before searching."
INVALID_DATE_RANGE_MSG = (
    "⚠️ **Invalid Date Range:** The start date cannot be after the end date. "
    "Please check your date bounds and try again."
)


def _has_inverted_date_range(
        query: str,
        start_date: Optional[str],
        end_date: Optional[str],
) -> bool:
    if start_date and end_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
            if start_dt > end_dt:
                return True
        except ValueError:
            pass

    iso_dates = re.findall(r"\b(\d{4}-\d{2}-\d{2})\b", query)
    if len(iso_dates) >= 2:
        try:
            d1 = datetime.strptime(iso_dates[0], "%Y-%m-%d").date()
            d2 = datetime.strptime(iso_dates[1], "%Y-%m-%d").date()
            if d1 > d2:
                return True
        except ValueError:
            pass
    return False


def _is_multi_day_or_range(
        query_lower: str,
        start_date: Optional[str],
        end_date: Optional[str],
) -> bool:
    if any(kw in query_lower for kw in HISTORICAL_RANGE_KEYWORDS):
        return True
    if start_date and end_date:
        return start_date != end_date
    return bool(start_date or end_date)


def _should_display_chart(query_lower: str, market_data_payload: dict[str, Any]) -> bool:
    if "should_render_chart" in market_data_payload:
        return bool(market_data_payload.get("should_render_chart")) and any(
            kw in query_lower for kw in CHART_KEYWORDS
        )
    return any(kw in query_lower for kw in CHART_KEYWORDS)


def _resolve_fallback_ticker(query_lower: str) -> str:
    if "googl" in query_lower or "google" in query_lower:
        return "GOOGL"
    if "msft" in query_lower or "microsoft" in query_lower:
        return "MSFT"
    if "aapl" in query_lower or "apple" in query_lower:
        return "AAPL"
    return "STOCK"


def _build_error_message(query: str, content: str, cache_icon: str = "🛡️") -> dict[str, Any]:
    return {
        "query": query,
        "content": content,
        "chart_ticker": "N/A",
        "requested_period": "1d",
        "should_render_chart": False,
        "execution_time": "0.01s",
        "render_id": uuid.uuid4().hex[:8],
        "historical_closes": {},
        "start_date": None,
        "end_date": None,
        "cache_icon": cache_icon,
    }


def _compute_compliance_if_needed(query_lower: str, active_user_data: dict[str, Any]) -> Any:
    if not any(kw in query_lower for kw in COMPLIANCE_KEYWORDS):
        return None
    holdings = active_user_data.get("holdings", {})
    if not holdings:
        return None

    enriched: dict[str, dict[str, Any]] = {}
    for ticker, info in holdings.items():
        avg_cost = float(info.get("avg_cost", 0.0))
        live_res = fetch_live_market_data(ticker)
        curr_price = (
            float(live_res.get("current_price", avg_cost))
            if isinstance(live_res, dict)
            else avg_cost
        )
        enriched[ticker] = {
            "shares": info.get("shares", 0),
            "current_price": curr_price,
        }
    return evaluate_portfolio_compliance(enriched)


def render_assistant_chat_tab(
        active_user_id: str,
        active_user_data: dict[str, Any],
        selected_admin_target: str | None,
        chat_api_url: str,
) -> None:
    active_name = active_user_data.get("name", "User")
    render_subheader_card(f"💬 Conversational Multi-Agent Execution ({active_name})")

    status_container = st.empty()
    user_query = st.chat_input(
        "🔍  Ask about market prices, pull historical stock prices, DCF valuations, or portfolio risk...",
        key="main_chat_input",
    )

    render_clear_chat_history_button(key="clear_chat_history_below_input_btn")

    if user_query is not None:
        if not _has_meaningful_query(user_query):
            st.warning(f"⚠️ {EMPTY_CHAT_QUERY_MSG}")
        else:
            query_start_time = time.time()
            is_safe, clean_query, err_msg = sanitize_and_validate_input(user_query)

            if not is_safe:
                st.error(
                    f"🛡️ Request Blocked for {user_query.strip()!r}: "
                    f"{err_msg or 'Query includes instructions outside safe financial research.'}"
                )
            else:
                q_lower = clean_query.lower()
                target_uid = selected_admin_target if selected_admin_target else active_user_id
                logger.info("Processing chat query='%s' session=%s", clean_query, st.session_state.session_id)

                scope_key = f"user:{target_uid}" if any(kw in q_lower for kw in PRIVATE_QUERY_KEYWORDS) else "global"
                extracted_start, extracted_end = extract_and_normalize_dates(clean_query)

                if (
                        (has_date_reference(clean_query) and not extracted_start and not extracted_end)
                        or _has_inverted_date_range(clean_query, extracted_start, extracted_end)
                ):
                    add_message_to_history(
                        _build_error_message(clean_query, INVALID_DATE_RANGE_MSG)
                    )
                    st.rerun()
                    return

                is_price_lookup = any(kw in q_lower for kw in PRICE_TABLE_KEYWORDS)
                wants_historical_closes = _is_multi_day_or_range(q_lower, extracted_start, extracted_end)

                query_embedding = get_embedding(clean_query)
                cached_payload = None
                if query_embedding:
                    cached_payload = run_async(
                        get_semantic_cache(
                            query_embedding,
                            scope_key=scope_key,
                            threshold=0.85,
                            start_date=extracted_start,
                            end_date=extracted_end,
                            query_text=clean_query,
                            require_closes=wants_historical_closes,
                        )
                    )

                if cached_payload and wants_historical_closes and not cached_payload.get("full_historical_closes"):
                    logger.warning("Cached historical payload missing closes; bypassing cache.")
                    cached_payload = None

                if cached_payload:
                    logger.info("Semantic cache hit for chat query.")
                    assistant_response = str(cached_payload.get("final_response", "") or "").strip()
                    market_data_payload = cached_payload.get("market_data", {})
                    historical_closes_payload = cached_payload.get("full_historical_closes", {})
                    active_ticker = (
                            market_data_payload.get("ticker")
                            or cached_payload.get("last_active_ticker")
                            or _resolve_fallback_ticker(q_lower)
                    )
                    start_date = extracted_start or market_data_payload.get("start_date")
                    end_date = extracted_end or market_data_payload.get("end_date")
                    show_table = wants_historical_closes and len(historical_closes_payload) >= 2
                    wants_chart = show_table and _should_display_chart(q_lower, market_data_payload)

                    if not assistant_response or "No data available" in assistant_response or len(assistant_response) < 30:
                        if show_table:
                            table_md = format_daywise_price_table(
                                historical_closes_payload,
                                start_date=start_date,
                                end_date=end_date,
                            )
                            assistant_response = (
                                f"### 📊 {active_ticker} Analysis\n\n"
                                f"#### Historical Daily Closing Prices (from {start_date or 'Start'} to {end_date or 'End'})\n"
                                f"{table_md}\n\n"
                                f"*Retrieved from semantic cache.*"
                            )

                    if assistant_response or historical_closes_payload:
                        add_message_to_history(
                            {
                                "query": clean_query,
                                "content": assistant_response,
                                "chart_ticker": active_ticker,
                                "requested_period": "1d",
                                "should_render_chart": wants_chart,
                                "execution_time": f"{time.time() - query_start_time:.3f}s",
                                "render_id": uuid.uuid4().hex[:8],
                                "historical_closes": historical_closes_payload if show_table else {},
                                "start_date": start_date if show_table else None,
                                "end_date": end_date if show_table else None,
                                "cache_icon": "⚡",
                            }
                        )
                        st.rerun()
                    else:
                        st.warning("⚠️ Cached response had no content to display.")
                else:
                    request_payload = {
                        "user_query": clean_query,
                        "session_id": st.session_state.session_id,
                        "active_user_id": target_uid,
                        "precomputed_compliance": _compute_compliance_if_needed(q_lower, active_user_data),
                    }

                    should_rerun = False
                    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                        future = executor.submit(requests.post, chat_api_url, json=request_payload, timeout=120)
                        while not future.done():
                            elapsed = time.time() - query_start_time
                            status_container.markdown(
                                f"<div style='color: #38bdf8; font-weight: 600; font-size: 13px; margin-bottom: 8px;'>"
                                f"⏱️ Executing optimized multi-agent workflow... ({elapsed:.2f}s)</div>",
                                unsafe_allow_html=True,
                            )
                            time.sleep(0.1)

                        status_container.empty()
                        formatted_time = f"{time.time() - query_start_time:.2f}s"

                        try:
                            response = future.result()
                            if response.status_code == 200:
                                data = response.json()
                                assistant_response = str(data.get("final_response", "") or "").strip()
                                market_data_payload = data.get("market_data", {})
                                raw_closes = data.get("full_historical_closes", {})
                                historical_closes_payload = (
                                    raw_closes if (is_price_lookup and isinstance(raw_closes, dict)) else {}
                                )
                                start_date = extracted_start or market_data_payload.get("start_date")
                                end_date = extracted_end or market_data_payload.get("end_date")

                                active_ticker = market_data_payload.get("ticker") or data.get("last_active_ticker")
                                if not active_ticker or active_ticker in {"NONE", "FETCH"}:
                                    active_ticker = _resolve_fallback_ticker(q_lower)

                                show_table = wants_historical_closes and len(historical_closes_payload) >= 2

                                if (
                                        show_table
                                        and "Historical Daily Closing Prices" not in assistant_response
                                        and historical_closes_payload
                                ):
                                    table_md = format_daywise_price_table(
                                        historical_closes_payload,
                                        start_date=start_date,
                                        end_date=end_date,
                                    )
                                    prefix = (
                                        f"### 📊 {active_ticker} Analysis\n\n"
                                        f"#### Historical Daily Closing Prices (from {start_date or 'Start'} to {end_date or 'End'})\n"
                                        f"{table_md}"
                                    )
                                    assistant_response = f"{prefix}\n\n{assistant_response}" if assistant_response else prefix

                                if not assistant_response and not historical_closes_payload:
                                    st.warning("⚠️ No response content was returned for your query.")
                                else:
                                    wants_chart = show_table and _should_display_chart(q_lower, market_data_payload)
                                    cache_icon = "🔍" if data.get("retrieved_documents") else "🧠"

                                    add_message_to_history(
                                        {
                                            "query": clean_query,
                                            "content": assistant_response,
                                            "chart_ticker": active_ticker,
                                            "requested_period": "1d",
                                            "should_render_chart": wants_chart,
                                            "execution_time": formatted_time,
                                            "render_id": uuid.uuid4().hex[:8],
                                            "historical_closes": historical_closes_payload if show_table else {},
                                            "start_date": start_date if show_table else None,
                                            "end_date": end_date if show_table else None,
                                            "cache_icon": cache_icon,
                                        }
                                    )

                                    if (
                                            query_embedding
                                            and not assistant_response.startswith("⚠️")
                                            and (not wants_historical_closes or historical_closes_payload)
                                    ):
                                        run_async(
                                            set_semantic_cache(
                                                query_embedding=query_embedding,
                                                scope_key=scope_key,
                                                query_text=clean_query,
                                                response_data=data,
                                                start_date=extracted_start,
                                                end_date=extracted_end,
                                            )
                                        )
                                    should_rerun = True
                            elif response.status_code == 400:
                                detail = "Request blocked by fiduciary risk or date validation guardrails."
                                try:
                                    err_json = response.json()
                                    if isinstance(err_json, dict) and err_json.get("detail"):
                                        detail = str(err_json["detail"])
                                except Exception:
                                    pass
                                add_message_to_history(
                                    _build_error_message(
                                        clean_query,
                                        f"🛡️ **Risk Guardrail Notice:** {detail}",
                                    )
                                )
                                should_rerun = True
                            else:
                                st.error(f"API Error [{response.status_code}]")
                        except Exception as exc:
                            logger.error("FastAPI gateway request failed: %s", exc)
                            st.error(f"Failed to connect to FastAPI gateway: {exc}")

                    if should_rerun:
                        st.rerun()

    st.markdown("---")
    render_paginated_chat_history()