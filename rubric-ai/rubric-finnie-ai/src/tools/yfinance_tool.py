from datetime import datetime, timedelta
from functools import lru_cache
import logging
import re
from typing import Any, Optional

from langchain_core.tools import tool
import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)

@lru_cache(maxsize=64)
def fetch_live_market_data(ticker_symbol: str) -> dict[str, Any]:
    """Fetches cached live market metrics for a given ticker symbol."""
    symbol = ticker_symbol.upper().strip()
    fallback_data: dict[str, Any] = {
        "ticker": symbol,
        "current_price": 0.0,
        "previous_close": 0.0,
        "pe_ratio": "N/A",
        "forward_pe": "N/A",
        "market_cap": "N/A",
        "volume": "N/A",
        "fifty_two_week_high": "N/A",
        "fifty_two_week_low": "N/A",
        "status": "fallback_error",
    }

    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info or {}

        current_price = (
                info.get("currentPrice")
                or info.get("regularMarketPrice")
                or info.get("previousClose")
        )
        previous_close = info.get("previousClose") or info.get("regularMarketPreviousClose") or 0.0

        if not current_price:
            fast_info = getattr(ticker, "fast_info", None)
            current_price = getattr(fast_info, "last_price", 0.0) if fast_info else 0.0
            if not previous_close:
                previous_close = getattr(fast_info, "previous_close", 0.0) if fast_info else 0.0

        return {
            "ticker": symbol,
            "current_price": float(current_price) if current_price else 0.0,
            "previous_close": float(previous_close) if previous_close else 0.0,
            "pe_ratio": info.get("trailingPE") or info.get("peRatio") or "N/A",
            "forward_pe": info.get("forwardPE") or "N/A",
            "market_cap": info.get("marketCap", "N/A"),
            "volume": info.get("volume", "N/A"),
            "fifty_two_week_high": info.get("fiftyTwoWeekHigh", "N/A"),
            "fifty_two_week_low": info.get("fiftyTwoWeekLow", "N/A"),
            "status": "success",
        }
    except Exception as exc:
        logger.error("Failed to fetch live market data for %s: %s", symbol, exc)
        return fallback_data

def get_portfolio_market_snapshot(holdings: dict[str, dict[str, Any]]) -> dict[str, Any]:
    prices: dict[str, float] = {}
    fundamentals: dict[str, dict[str, Any]] = {}

    for ticker in holdings.keys():
        live_data = fetch_live_market_data(ticker)
        prices[ticker] = live_data["current_price"]
        fundamentals[ticker] = {
            "pe_ratio": live_data["pe_ratio"],
            "forward_pe": live_data["forward_pe"],
            "market_cap": live_data["market_cap"],
            "volume": live_data["volume"],
            "52w_high": live_data["fifty_two_week_high"],
            "52w_low": live_data["fifty_two_week_low"],
        }

    return {"prices": prices, "fundamentals": fundamentals}

def parse_period_to_days(period_str: str) -> int:
    normalized = str(period_str).lower().strip()
    if normalized in {"max", "all", "all-time", "history"}:
        return -1

    match = re.search(r"(\d+)\s*([a-z]+)", normalized)
    if not match:
        return 365

    val = int(match.group(1))
    unit = match.group(2)
    if unit.startswith("y"):
        return val * 365
    if unit.startswith("m"):
        return val * 30
    if unit.startswith("w"):
        return val * 7
    if unit.startswith("d"):
        return val
    return 365

@lru_cache(maxsize=64)
def fetch_historical_prices(
        ticker_symbol: str,
        period: str = "max",
        start: Optional[str] = None,
        end: Optional[str] = None,
        interval: Optional[str] = None,
) -> pd.DataFrame:
    """Fetches historical OHLCV price series with inclusive end-date handling."""
    symbol = ticker_symbol.upper().strip()
    try:
        req_period = (period or "max").lower().strip()
        resolved_interval = interval or (
            "1m" if req_period == "1d" else "15m" if req_period == "5d" else "1d"
        )

        today_str = datetime.today().strftime("%Y-%m-%d")
        resolved_end = today_str if (end and end > today_str) else end

        if start and resolved_end:
            try:
                exclusive_end = (
                        datetime.strptime(resolved_end, "%Y-%m-%d") + timedelta(days=1)
                ).strftime("%Y-%m-%d")
            except Exception:
                exclusive_end = resolved_end
            hist_df = yf.download(
                symbol,
                start=start,
                end=exclusive_end,
                interval=resolved_interval,
                progress=False,
                auto_adjust=True,
            )
        elif req_period in {"1d", "5d", "max"} or parse_period_to_days(req_period) == -1:
            yf_period = "max" if parse_period_to_days(req_period) == -1 else req_period
            hist_df = yf.download(
                symbol,
                period=yf_period,
                interval=resolved_interval,
                progress=False,
                auto_adjust=True,
            )
        else:
            total_days = parse_period_to_days(req_period)
            end_dt = datetime.today()
            start_dt = end_dt - timedelta(days=total_days)
            hist_df = yf.download(
                symbol,
                start=start_dt.strftime("%Y-%m-%d"),
                end=end_dt.strftime("%Y-%m-%d"),
                interval=resolved_interval,
                progress=False,
                auto_adjust=True,
            )

        if isinstance(hist_df.columns, pd.MultiIndex):
            hist_df.columns = hist_df.columns.get_level_values(0)

        return hist_df
    except Exception as exc:
        logger.error("Failed to fetch historical prices for %s: %s", symbol, exc)
        return pd.DataFrame()

@tool
def get_historical_prices_tool(ticker_symbol: str, period: str = "max") -> str:
    """Fetches recent historical OHLCV price data for a given ticker."""
    df = fetch_historical_prices(ticker_symbol, period=period)
    if df.empty:
        return f"No historical data found for {ticker_symbol}."
    return df.tail(10).to_string()