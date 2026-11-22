import logging
from typing import Any

from langchain_core.runnables import RunnableConfig
import pandas as pd

from src.agent.nodes.market_node import (
    calculate_macd,
    calculate_rsi,
    execute_market_data_lookup,
    execute_market_synthesis,
)
from src.agent.state import FinancialAssistantState

logger = logging.getLogger(__name__)


def market_data_node(state: FinancialAssistantState, config: RunnableConfig) -> dict[str, Any]:
    """Agent 1: Dynamically handles portfolio lookups, RAG valuation searches, and market data."""
    logger.info("Executing market_data_node | Session ID: %s", state.get("session_id"))
    return execute_market_data_lookup(state)


def technical_indicator_node(
        state: FinancialAssistantState,
        config: RunnableConfig,
) -> dict[str, Any]:
    """Agent 2: Computes technical momentum indicators dynamically if an active ticker is present."""
    ticker = state.get("last_active_ticker")
    market_data = dict(state.get("market_data", {}))
    full_closes = state.get("full_historical_closes", {})
    logger.info("Executing technical_indicator_node | Ticker: %s", ticker)

    if state.get("final_response") or not ticker or not market_data:
        logger.debug("Skipping technical indicators: final response already set or no active ticker/market data.")
        return {
            "current_step": "technical_indicators_skipped",
            "last_active_ticker": ticker,
        }

    existing_techs = market_data.get("technicals") or {}
    rsi_val = existing_techs.get("RSI_14")
    macd_val = existing_techs.get("MACD_signal")

    close_series = pd.Series(list(full_closes.values()), dtype=float) if full_closes else pd.Series(dtype=float)
    if rsi_val is None and len(close_series) >= 15:
        rsi_val = calculate_rsi(close_series, period=14)
    if not macd_val and len(close_series) >= 12:
        macd_val = calculate_macd(close_series)

    if rsi_val is not None:
        if rsi_val >= 70:
            rsi_regime = "Overbought"
        elif rsi_val <= 30:
            rsi_regime = "Oversold"
        else:
            rsi_regime = "Neutral / Constructive"
    else:
        rsi_regime = None

    updated_techs: dict[str, Any] = {}
    if rsi_val is not None:
        updated_techs["RSI_14"] = rsi_val
        updated_techs["RSI_regime"] = rsi_regime
    if macd_val:
        updated_techs["MACD_signal"] = macd_val

    return {
        "current_step": "technical_indicators_computed",
        "last_active_ticker": ticker,
        "market_data": {
            **market_data,
            "technicals": updated_techs,
        },
    }


def sentiment_node(state: FinancialAssistantState, config: RunnableConfig) -> dict[str, Any]:
    """Agent 3: Evaluates available sentiment context without fabricating static scores."""
    ticker = state.get("last_active_ticker")
    market_data = state.get("market_data", {})
    logger.info("Executing sentiment_node | Ticker: %s", ticker)

    if state.get("final_response") or not ticker or not market_data:
        logger.debug("Skipping sentiment analysis: final response already set or no active ticker/market data.")
        return {
            "current_step": "sentiment_skipped",
            "last_active_ticker": ticker,
        }

    existing_score = market_data.get("sentiment_score")
    existing_label = market_data.get("sentiment_label") or (
        "Available in context" if existing_score is not None else "Not available in live feed"
    )

    return {
        "current_step": "sentiment_analyzed",
        "last_active_ticker": ticker,
        "market_data": {
            **market_data,
            "sentiment_score": existing_score,
            "sentiment_label": existing_label,
        },
    }


def run_market_analysis_node(
        state: FinancialAssistantState,
        config: RunnableConfig,
) -> dict[str, Any]:
    """Synthesizes final market analysis response."""
    logger.info("Executing run_market_analysis_node | Ticker: %s", state.get("last_active_ticker"))
    return execute_market_synthesis(state)