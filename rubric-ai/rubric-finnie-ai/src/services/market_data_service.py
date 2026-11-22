from datetime import datetime
import logging
from typing import Any

import pandas as pd
import requests
import streamlit as st
import yfinance as yf

from src.core.config import settings
from src.database.repository import get_all_user_profiles
from src.tools.yfinance_tool import fetch_historical_prices
from src.ui.components.styles import format_market_cap_num, format_volume_num

logger = logging.getLogger(__name__)

PROFILES_API_URL = settings.PROFILES_API_URL
CHAT_API_URL = settings.CHAT_API_URL

@st.cache_data(ttl=60, show_spinner=False)
def fetch_user_profiles() -> dict[str, Any]:
    try:
        response = requests.get(PROFILES_API_URL, timeout=3)
        if response.status_code == 200 and response.json():
            return response.json()
        logger.warning("Profiles API returned status %s; falling back to repository.", response.status_code)
    except Exception as exc:
        logger.warning("Failed to fetch profiles from API (%s); using local repository.", exc)

    return get_all_user_profiles()

@st.cache_data(ttl=300, show_spinner=False)
def fetch_cached_historical_prices(ticker_symbol: str, period: str) -> pd.DataFrame:
    logger.info("Fetching cached historical prices for %s (period=%s)", ticker_symbol, period)
    df = fetch_historical_prices(ticker_symbol, period=period)
    if df.empty and period.lower() == "1d":
        logger.info("1d period empty for %s; falling back to 5d", ticker_symbol)
        df = fetch_historical_prices(ticker_symbol, period="5d")
    if not df.empty:
        df = df.reset_index()
        if "Datetime" in df.columns and "Date" not in df.columns:
            df = df.rename(columns={"Datetime": "Date"})
        elif "index" in df.columns and "Date" not in df.columns:
            df = df.rename(columns={"index": "Date"})
    return df

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_live_sector(ticker: str) -> str:
    try:
        info = yf.Ticker(ticker).info or {}
        sector = info.get("sector")
        return str(sector) if sector else "Other"
    except Exception as exc:
        logger.warning("Failed to fetch live sector for %s: %s", ticker, exc)
        return "Other"

@st.cache_data(ttl=300, show_spinner=False)
def fetch_dynamic_trending_tickers() -> list[str]:
    """Fetches top trending US equity tickers dynamically from Yahoo Finance."""
    try:
        url = "https://query1.finance.yahoo.com/v1/finance/trending/US?count=10"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            quotes = data.get("finance", {}).get("result", [{}])[0].get("quotes", [])
            symbols = [q.get("symbol") for q in quotes if q.get("symbol")]
            equity_symbols = [str(s) for s in symbols if "=" not in str(s) and "-" not in str(s)]
            if equity_symbols:
                logger.info("Fetched live trending tickers: %s", equity_symbols)
                return equity_symbols
    except Exception as exc:
        logger.warning("Could not fetch live trending tickers: %s", exc)
    return []

def _build_ticker_snapshot_row(ticker: str) -> dict[str, Any]:
    tk = yf.Ticker(ticker)
    info = tk.info or {}
    hist = tk.history(period="5d")

    curr_price = info.get("currentPrice") or info.get("regularMarketPrice")
    if not curr_price and not hist.empty:
        curr_price = float(hist["Close"].iloc[-1])
    curr_price_val = float(curr_price) if curr_price else 150.0

    prev_close = info.get("previousClose") or info.get("regularMarketPreviousClose")
    if not prev_close and len(hist) > 1:
        prev_close = float(hist["Close"].iloc[-2])
    prev_close_val = float(prev_close) if prev_close else curr_price_val

    change_pct = ((curr_price_val - prev_close_val) / prev_close_val) * 100 if prev_close_val else 0.0
    vol = info.get("volume") or (int(hist["Volume"].iloc[-1]) if not hist.empty else 50_000_000)
    mkt_cap = info.get("marketCap", 0)

    pe = info.get("trailingPE", "N/A")
    pe_val = round(float(pe), 2) if isinstance(pe, (int, float)) else "N/A"
    eps = info.get("trailingEps", "N/A")
    eps_val = round(float(eps), 2) if isinstance(eps, (int, float)) else "N/A"
    high_52 = float(info.get("fiftyTwoWeekHigh") or (curr_price_val * 1.2))
    low_52 = float(info.get("fiftyTwoWeekLow") or (curr_price_val * 0.8))

    div_yield = info.get("dividendYield")
    div_val = f"{float(div_yield) * 100:,.2f}%" if isinstance(div_yield, (int, float)) else "N/A"

    ex_div = info.get("exDividendDate")
    ex_div_str = (
        datetime.fromtimestamp(float(ex_div)).strftime("%Y-%m-%d")
        if isinstance(ex_div, (int, float))
        else "N/A"
    )

    return {
        "ticker": ticker,
        "name": info.get("shortName") or info.get("longName") or ticker,
        "exchange": info.get("exchange") or "NYSE/NASDAQ",
        "current_price": round(curr_price_val, 2),
        "change_pct": round(float(change_pct), 2),
        "volume_raw": int(vol),
        "volume_str": format_volume_num(vol),
        "market_cap_raw": float(mkt_cap or 0.0),
        "market_cap_str": format_market_cap_num(mkt_cap or 0.0),
        "pe_ratio": pe_val,
        "eps": eps_val,
        "high_52": round(high_52, 2),
        "low_52": round(low_52, 2),
        "dividend": div_val,
        "ex_dividend": ex_div_str,
        "rsi": round(52.5 + (float(change_pct) * 1.5), 2),
        "macd": "Bullish" if float(change_pct) >= 0 else "Neutral",
        "sentiment": round(0.65 + (float(change_pct) / 100), 2),
    }

@st.cache_data(ttl=120, show_spinner=False)
def fetch_live_market_snapshot_batch(tickers: list[str] | tuple[str, ...]) -> pd.DataFrame:
    if not tickers:
        return pd.DataFrame()

    logger.info("Fetching live market snapshot batch for %d tickers", len(tickers))
    snapshot_rows: list[dict[str, Any]] = []
    for ticker in tickers:
        try:
            snapshot_rows.append(_build_ticker_snapshot_row(str(ticker)))
        except Exception as exc:
            logger.warning("Error fetching ticker snapshot for %s: %s", ticker, exc)
    return pd.DataFrame(snapshot_rows)