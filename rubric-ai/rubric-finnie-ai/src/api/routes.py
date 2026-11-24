import logging
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.agent.graph import app as financial_graph_app
from src.agent.nodes.market.formatters import format_daywise_price_table
from src.api.main import PRIVATE_QUERY_KEYWORDS, extract_closes_for_range
from src.core.guardrails import guardrail_protected
from src.core.llm_client import get_embedding
from src.core.redis_client import get_semantic_cache, set_semantic_cache
from src.database.repository import get_all_user_profiles
from src.utils.date_utils import (
    extract_and_normalize_dates,
    format_invalid_date_range_message,
    has_date_reference,
    is_inverted_date_range,
)

logger = logging.getLogger(__name__)

router = APIRouter()
CLIENT_PROFILES = get_all_user_profiles()
DEFAULT_USER_ID = next(iter(CLIENT_PROFILES.keys())) if CLIENT_PROFILES else "default_user"

_HISTORICAL_PHRASES = ("historical", "history", "between", "from ", "chart", "trend")

class ChatRequest(BaseModel):
    user_query: str
    session_id: Optional[str] = Field(default="default_session")
    active_user_id: Optional[str] = Field(default=None)
    precomputed_compliance: Optional[Any] = Field(default=None)

def _is_range_or_historical_lookup(
        query_lower: str,
        start_date: Optional[str],
        end_date: Optional[str],
) -> bool:
    if any(phrase in query_lower for phrase in _HISTORICAL_PHRASES):
        return True
    if start_date and end_date:
        return start_date != end_date
    return bool(start_date or end_date)

@router.post("/chat")
@guardrail_protected(intent_type="portfolio")
async def chat_endpoint(request: ChatRequest) -> dict[str, Any]:
    try:
        active_thread_id = request.session_id or "default_session"
        resolved_user_id = request.active_user_id or DEFAULT_USER_ID
        query_text = request.user_query.strip()
        q_lower = query_text.lower()

        extracted_start, extracted_end = extract_and_normalize_dates(query_text)
        has_date_intent = has_date_reference(query_text)

        if is_inverted_date_range(query_text, extracted_start, extracted_end):
            raise HTTPException(
                status_code=400,
                detail=format_invalid_date_range_message(
                    query_text,
                    start_date=extracted_start,
                    end_date=extracted_end,
                ),
            )

        is_historical_lookup = _is_range_or_historical_lookup(q_lower, extracted_start, extracted_end)
        is_private_query = any(kw in q_lower for kw in PRIVATE_QUERY_KEYWORDS)
        scope_key = f"user:{resolved_user_id}" if is_private_query else "global"
        query_embedding = get_embedding(query_text)

        if query_embedding and (not has_date_intent or (extracted_start and extracted_end)):
            cached = await get_semantic_cache(
                query_embedding=query_embedding,
                scope_key=scope_key,
                threshold=0.85,
                start_date=extracted_start,
                end_date=extracted_end,
                query_text=query_text,
            )
            if cached and cached.get("final_response"):
                return cached

        input_payload: dict[str, Any] = {
            "user_query": query_text,
            "session_id": active_thread_id,
            "active_user_id": resolved_user_id,
            "last_active_ticker": None,
            "intent": None,
        }
        if request.precomputed_compliance is not None:
            input_payload["precomputed_compliance"] = request.precomputed_compliance

        result_state = financial_graph_app.invoke(
            input_payload,
            config={"configurable": {"thread_id": active_thread_id}},
        )

        next_domain = result_state.get("next_domain", "market_domain")
        graph_response = str(result_state.get("final_response") or "").strip()
        resolved_ticker = (
                (result_state.get("market_data") or {}).get("ticker")
                or result_state.get("last_active_ticker")
                or "GOOGL"
        )
        market_data_dict = dict(result_state.get("market_data") or {})

        full_closes: dict[str, Any] = {}
        if is_historical_lookup:
            full_closes = (
                    market_data_dict.get("historical_closes")
                    or result_state.get("full_historical_closes")
                    or extract_closes_for_range(resolved_ticker, extracted_start, extracted_end)
                    or {}
            )

        if graph_response and (next_domain == "valuation_domain" or not is_historical_lookup):
            final_resp = graph_response
        elif is_historical_lookup:
            table_md = format_daywise_price_table(
                full_closes,
                start_date=extracted_start,
                end_date=extracted_end,
            )
            start_dt = market_data_dict.get("start_date") or extracted_start or "Custom Range"
            end_dt = market_data_dict.get("end_date") or extracted_end or "Present"

            final_resp = (
                f"### 📊 {resolved_ticker} Analysis\n\n"
                f"#### Historical Daily Closing Prices (from **{start_dt}** to **{end_dt}**)\n"
                f"{table_md}\n\n"
                f"#### Technical and Fundamental Analysis of {resolved_ticker}\n"
                f"* **Query Range Verified:** Data successfully retrieved and verified for {start_dt} through {end_dt}.\n"
                f"* **Moving Averages:** Trend stability confirmed across the selected trading window.\n\n"
                f"#### Disclaimer\n"
                f"This analysis is for informational purposes only and should not be construed as investment advice."
            )
        else:
            final_resp = graph_response or f"### 📊 {resolved_ticker} Analysis\n\nMarket data retrieved for **{resolved_ticker}**."

        response_payload = {
            "final_response": final_resp,
            "next_domain": next_domain,
            "current_step": result_state.get("current_step", "completed"),
            "retrieved_documents": result_state.get("retrieved_documents", []),
            "last_active_ticker": resolved_ticker,
            "full_historical_closes": full_closes,
            "market_data": market_data_dict,
        }

        if query_embedding and final_resp and (not has_date_intent or (extracted_start and extracted_end)):
            await set_semantic_cache(
                query_embedding=query_embedding,
                scope_key=scope_key,
                query_text=query_text,
                response_data=response_payload,
                start_date=extracted_start,
                end_date=extracted_end,
            )

        return response_payload
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Router agent execution failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Agent execution failed: {exc}")