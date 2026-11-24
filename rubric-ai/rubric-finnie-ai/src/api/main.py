# src/api/main.py
from contextlib import asynccontextmanager
from datetime import datetime
import logging
from pathlib import Path
from typing import Any, Optional
import warnings

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pandas.errors import Pandas4Warning
import pandas as pd
from pydantic import BaseModel, Field

env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path, override=True)

from src.agent.graph import financial_graph as financial_graph_app
from src.agent.nodes.market.formatters import format_daywise_price_table
from src.core.llm_client import get_embedding
from src.core.redis_client import checkpointer, get_semantic_cache, set_semantic_cache
from src.database.repository import get_all_user_profiles, get_user_profile
from src.services.trading_service import execute_trade
from src.tools.yfinance_tool import fetch_historical_prices
from src.utils.date_utils import (
    extract_and_normalize_dates,
    format_invalid_date_range_message,
    has_date_reference,
    is_inverted_date_range,
)

warnings.simplefilter(action="ignore", category=Pandas4Warning)
logger = logging.getLogger(__name__)

PRIVATE_QUERY_KEYWORDS = ("portfolio", "holding", "my asset", "allocation", "balance", "trade")

def extract_closes_for_range(
        ticker: str,
        start_date: Optional[str],
        end_date: Optional[str],
) -> dict[str, float]:
    if not start_date or not end_date or is_inverted_date_range("", start_date, end_date):
        return {}

    df_hist = fetch_historical_prices(ticker, start=start_date, end=end_date)
    if df_hist.empty:
        return {}

    df_hist.index = pd.to_datetime(df_hist.index).tz_localize(None)
    mask = (df_hist.index >= pd.to_datetime(start_date)) & (df_hist.index <= pd.to_datetime(end_date))
    df_filtered = df_hist.loc[mask]
    if df_filtered.empty:
        df_filtered = df_hist

    temp_df = df_filtered.reset_index()
    date_col = "Date" if "Date" in temp_df.columns else temp_df.columns[0]
    temp_df["DateStr"] = pd.to_datetime(temp_df[date_col]).dt.strftime("%Y-%m-%d")
    return dict(zip(temp_df["DateStr"], df_filtered["Close"].astype(float)))

def _build_historical_fallback_response(
        ticker: str,
        closes: dict[str, Any],
        start_dt: Optional[str],
        end_dt: Optional[str],
) -> str:
    table_md = (
        format_daywise_price_table(closes)
        if closes
        else "| Date | Closing Price |\n|---|---|\n| N/A | No data available |"
    )
    resolved_start = start_dt or "Custom Range"
    resolved_end = end_dt or "Present"
    return (
        f"### 📊 {ticker} Analysis\n\n"
        f"#### Historical Daily Closing Prices (from **{resolved_start}** to **{resolved_end}**)\n"
        f"{table_md}\n\n"
        f"*Market data successfully retrieved and verified for the requested date range.*"
    )

def _chat_response_from_payload(
        *,
        session_id: str,
        user_id: str,
        payload: dict[str, Any],
        errors: Optional[list[str]] = None,
) -> "ChatResponse":
    return ChatResponse(
        session_id=payload.get("session_id", session_id),
        active_user_id=payload.get("active_user_id", user_id),
        current_step=payload.get("current_step", "completed"),
        next_domain=payload.get("next_domain", "general"),
        user_profile=payload.get("user_profile", {}),
        portfolio_holdings=payload.get("portfolio_holdings", {}),
        retrieved_documents=payload.get("retrieved_documents", []),
        market_data=payload.get("market_data", {}),
        valuation_data=payload.get("valuation_data", {}),
        risk_data=payload.get("risk_data", {}),
        final_response=payload.get("final_response", ""),
        errors=errors if errors is not None else [],
        last_active_ticker=payload.get("last_active_ticker"),
        full_historical_closes=payload.get("full_historical_closes", {}),
    )

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await checkpointer.asetup()
        logger.info("AsyncRedisSaver checkpointer indices initialized successfully.")
    except Exception as exc:
        logger.error("Failed to initialize Redis checkpointer indices: %s", exc)
        raise
    yield

app = FastAPI(
    title="Rubric AI - Financial Assistant API",
    description="Asynchronous multi-agent orchestration gateway for financial analysis, valuation, and risk management.",
    version="1.0.0",
    lifespan=lifespan,
)

class ChatRequest(BaseModel):
    user_query: str = Field(..., description="The financial query or request from the user.")
    session_id: str = Field(default="default_session", description="Session identifier for continuity.")
    active_user_id: str = Field(default="C4820198", description="Active investor profile ID.")
    precomputed_compliance: Optional[dict[str, Any]] = Field(
        default=None,
        description="Pre-computed compliance data payload.",
    )

class TradeRequest(BaseModel):
    user_id: str = Field(..., description="User ID executing the trade.")
    ticker: str = Field(..., description="Target stock ticker symbol.")
    action: str = Field(..., description="Trade action: 'BUY' or 'SELL'.")
    shares: float = Field(..., description="Number of shares to trade.")
    execution_price: float = Field(..., description="Simulated execution price per share.")

class ChatResponse(BaseModel):
    session_id: str
    active_user_id: str
    current_step: str
    next_domain: str
    user_profile: dict[str, Any]
    portfolio_holdings: dict[str, Any]
    retrieved_documents: list[dict[str, Any]]
    market_data: dict[str, Any]
    valuation_data: dict[str, Any]
    risk_data: dict[str, Any]
    final_response: str
    errors: list[str]
    last_active_ticker: Optional[str] = None
    full_historical_closes: Optional[dict[str, float]] = Field(default_factory=dict)

@app.get("/health", tags=["System"])
async def health_check() -> dict[str, str]:
    return {"status": "healthy", "service": "Rubric AI Financial Assistant API"}

@app.post("/api/v1/chat", response_model=ChatResponse, tags=["Agent Execution"])
async def execute_financial_chat(request: ChatRequest) -> ChatResponse:
    try:
        active_thread_id = request.session_id or "default_session"
        profiles = get_all_user_profiles()
        resolved_user_id = request.active_user_id or next(iter(profiles.keys()), "default_user")
        query_text = request.user_query.strip()

        extracted_start, extracted_end = extract_and_normalize_dates(query_text)
        has_date_intent = has_date_reference(query_text)

        if (
                (has_date_intent and not extracted_start and not extracted_end)
                or is_inverted_date_range(query_text, extracted_start, extracted_end)
        ):
            invalid_msg = format_invalid_date_range_message(
                query_text,
                start_date=extracted_start,
                end_date=extracted_end,
            )
            return _chat_response_from_payload(
                session_id=active_thread_id,
                user_id=resolved_user_id,
                payload={
                    "current_step": "guardrail_rejected",
                    "next_domain": "general",
                    "final_response": invalid_msg,
                },
                errors=["Invalid date range: start date is after end date"],
            )

        is_private_query = any(kw in query_text.lower() for kw in PRIVATE_QUERY_KEYWORDS)
        scope_key = f"user:{resolved_user_id}" if is_private_query else "global"
        query_embedding = get_embedding(query_text)

        if query_embedding and (not has_date_intent or (extracted_start and extracted_end)):
            cached = await get_semantic_cache(
                query_embedding=query_embedding,
                scope_key=scope_key,
                query_text=query_text,
                threshold=0.85,
                start_date=extracted_start,
                end_date=extracted_end,
            )
            if cached and cached.get("full_historical_closes"):
                return _chat_response_from_payload(
                    session_id=active_thread_id,
                    user_id=resolved_user_id,
                    payload=cached,
                    errors=[],
                )

        active_profile = profiles.get(resolved_user_id, profiles.get(next(iter(profiles.keys())), {}))
        initial_state = {
            "user_query": query_text,
            "session_id": active_thread_id,
            "active_user_id": resolved_user_id,
            "user_profile": {
                "name": active_profile.get("name", "Valued Client"),
                "risk_tolerance": active_profile.get("risk_tolerance", "Moderate"),
                "investment_horizon": active_profile.get("investment_horizon", "Long-term"),
            },
            "portfolio_holdings": active_profile.get("holdings", {}),
            "precomputed_compliance": request.precomputed_compliance,
            "last_active_ticker": None,
        }

        result = await financial_graph_app.ainvoke(
            initial_state,
            config={"configurable": {"thread_id": active_thread_id}},
        )

        resolved_ticker = result.get("last_active_ticker") or "GOOGL"
        market_data_dict = result.get("market_data", {})
        full_closes = (
                market_data_dict.get("historical_closes")
                or result.get("full_historical_closes")
                or extract_closes_for_range(resolved_ticker, extracted_start, extracted_end)
        )

        graph_final_response = result.get("final_response", "")
        if not graph_final_response or "No response generated" in graph_final_response:
            graph_final_response = _build_historical_fallback_response(
                resolved_ticker,
                full_closes,
                market_data_dict.get("start_date") or extracted_start,
                market_data_dict.get("end_date") or extracted_end,
                )

        response_payload = {
            "session_id": result.get("session_id", active_thread_id),
            "active_user_id": result.get("active_user_id", resolved_user_id),
            "current_step": "market_analysis_synthesized",
            "next_domain": result.get("next_domain", "general"),
            "user_profile": result.get("user_profile", {}),
            "portfolio_holdings": result.get("portfolio_holdings", {}),
            "retrieved_documents": result.get("retrieved_documents", []),
            "market_data": market_data_dict,
            "valuation_data": result.get("valuation_data", {}),
            "risk_data": result.get("risk_data", {}),
            "final_response": graph_final_response,
            "last_active_ticker": resolved_ticker,
            "full_historical_closes": full_closes,
        }

        if query_embedding and full_closes and (not has_date_intent or (extracted_start and extracted_end)):
            await set_semantic_cache(
                query_embedding=query_embedding,
                scope_key=scope_key,
                query_text=query_text,
                response_data=response_payload,
                start_date=extracted_start,
                end_date=extracted_end,
            )

        return _chat_response_from_payload(
            session_id=active_thread_id,
            user_id=resolved_user_id,
            payload=response_payload,
            errors=result.get("errors", []),
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Agent execution failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Agent execution failed: {exc}")

@app.post("/api/v1/trade", tags=["Trading"])
def post_mock_trade(request: TradeRequest) -> dict[str, str]:
    try:
        return execute_trade(
            user_id=request.user_id,
            ticker=request.ticker,
            action=request.action,
            shares=request.shares,
            price=request.execution_price,
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as exc:
        logger.error("Trade API error: %s", exc)
        raise HTTPException(status_code=500, detail=f"Internal trade execution error: {exc}")

@app.get("/api/v1/profiles", tags=["Profiles"])
async def get_user_profiles() -> dict[str, Any]:
    return get_all_user_profiles()

@app.get("/api/v1/profiles/{user_id}", tags=["Profiles"])
def get_single_profile(user_id: str) -> dict[str, Any]:
    profile = get_user_profile(user_id)
    if not profile:
        logger.warning("Profile requested not found: %s", user_id)
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile