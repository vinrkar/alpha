# src/mcp/client/financial_client.py

import asyncio
import concurrent.futures
from datetime import datetime
import json
import logging
import sys
from typing import Optional

from mcp import Client
import pandas as pd
import yfinance as yf

from src.mcp.financial_server import app as financial_server_app

logger = logging.getLogger(__name__)

def _normalize_price_dataframe(
        df: pd.DataFrame,
        start_date: str,
        end_date: str,
        parse_date_col: bool = False,
) -> pd.DataFrame:
    if df.empty:
        return df

    normalized = df.copy()
    if isinstance(normalized.columns, pd.MultiIndex):
        normalized.columns = normalized.columns.get_level_values(0)

    if parse_date_col and not normalized.empty:
        date_col = "Date" if "Date" in normalized.columns else normalized.columns[0]
        if date_col in normalized.columns:
            normalized[date_col] = pd.to_datetime(normalized[date_col])
            normalized.set_index(date_col, inplace=True)

    if not normalized.empty:
        normalized.index = pd.to_datetime(normalized.index)
        normalized = normalized.loc[start_date:end_date]

    return normalized

async def fetch_historical_prices_via_mcp_client(
        ticker: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
) -> pd.DataFrame:
    """Fetches historical prices via MCP Client with a direct yfinance fallback."""
    s_date = start_date or "2024-01-01"
    e_date = end_date or datetime.now().strftime("%Y-%m-%d")

    try:
        async with Client(financial_server_app) as client:
            result = await client.call_tool(
                "fetch_historical_prices",
                arguments={
                    "ticker": ticker,
                    "start_date": s_date,
                    "end_date": e_date,
                },
            )
            if result and result.content:
                for block in result.content:
                    raw_text = getattr(block, "text", None)
                    if (
                            raw_text
                            and not raw_text.startswith("Error")
                            and not raw_text.startswith("No data")
                    ):
                        df = pd.DataFrame(json.loads(raw_text))
                        return _normalize_price_dataframe(df, s_date, e_date, parse_date_col=True)
    except Exception as exc:
        logger.error("MCP v2 In-Process Client error: %s", exc, exc_info=True)

    try:
        fallback_df = yf.download(ticker, start=s_date, end=e_date)
        return _normalize_price_dataframe(fallback_df, s_date, e_date, parse_date_col=False)
    except Exception as exc:
        logger.error("Fallback historical price fetch failed for %s: %s", ticker, exc)
        return pd.DataFrame()

def run_mcp_client_sync(
        ticker: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
) -> pd.DataFrame:
    """Thread-safe synchronous entry point for LangGraph node invocation."""

    def _run_in_isolated_thread() -> pd.DataFrame:
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(
                fetch_historical_prices_via_mcp_client(ticker, start_date, end_date)
            )
        finally:
            loop.close()

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(_run_in_isolated_thread)
        try:
            return future.result(timeout=20)
        except concurrent.futures.TimeoutError:
            logger.error("MCP client call timed out for %s", ticker)
            return pd.DataFrame()