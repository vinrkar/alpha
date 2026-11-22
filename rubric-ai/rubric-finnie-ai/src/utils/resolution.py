# src/utils/resolution.py

import logging
import re
from typing import Any, Mapping, Optional

import yfinance as yf

logger = logging.getLogger(__name__)

RESERVED_CONTROL_TOKENS: set[str] = {
    "VALID",
    "INVALID",
    "TRUE",
    "FALSE",
    "SUCCESS",
    "ERROR",
    "PENDING",
    "N/A",
    "NONE",
    "NULL",
    "PORTFOLIO",
    "FETCH",
    "SHOW",
    "PULL",
    "GET",
    "ANALYZE",
    "CHECK",
    "FIND",
    "VIEW",
    "LIST",
    "DO",
    "BE",
    "AS",
    "IF",
    "TO",
    "IT",
}

IGNORED_NAME_WORDS: set[str] = {
    "inc",
    "corp",
    "cl",
    "a",
    "b",
    "co",
    "ltd",
    "plc",
    "holdings",
    "group",
    "com",
    "portfolio",
    "active",
    "summary",
    "positions",
    "my",
    "across",
    "search",
    "matching",
    "security",
    "ticker",
    "isin",
    "do",
    "i",
    "hold",
    "the",
}.union({token.lower() for token in RESERVED_CONTROL_TOKENS})

EXCLUDED_QUERY_WORDS: set[str] = RESERVED_CONTROL_TOKENS.union(
    {
        "WHAT",
        "HOW",
        "WHO",
        "WHERE",
        "WHEN",
        "WHY",
        "IS",
        "ARE",
        "THE",
        "AND",
        "FOR",
        "FROM",
        "WITH",
        "THIS",
        "THAT",
        "Q3",
        "Q1",
        "Q2",
        "Q4",
        "REVENUE",
        "GROWTH",
        "ME",
        "DETAILS",
        "VALUATION",
        "RATIO",
        "EARNINGS",
        "NOTES",
        "DOCUMENTS",
        "SHOW",
        "PULL",
        "GET",
        "ANALYZE",
        "CHECK",
        "OUR",
        "MY",
        "YOUR",
        "THEIR",
        "HIS",
        "HER",
        "ITS",
        "SEC",
        "INTERNAL",
        "SAY",
        "ABOUT",
        "TELL",
        "GIVE",
        "FIND",
        "MARGINS",
        "CASH",
        "FLOW",
    }
)

def resolve_ticker_from_isin(isin: str) -> str:
    """Resolves a ticker symbol from an ISIN via yfinance search, falling back to the ISIN."""
    isin_upper = isin.upper().strip()
    try:
        search_results = yf.Search(isin_upper, max_results=5)
        quotes = getattr(search_results, "quotes", []) or []
        for quote in quotes:
            symbol = str(quote.get("symbol", "")).upper()
            if (
                    symbol
                    and symbol not in RESERVED_CONTROL_TOKENS
                    and not any(ch in symbol for ch in (".", "="))
            ):
                return symbol
        if quotes:
            return str(quotes[0].get("symbol", isin_upper)).upper()
    except Exception as exc:
        logger.debug("ISIN lookup failed for %s: %s", isin_upper, exc)
    return isin_upper

def resolve_isin_from_ticker(ticker: str) -> str:
    """Resolves an ISIN from a ticker symbol via yfinance search, returning 'N/A' if unavailable."""
    ticker_upper = ticker.upper().strip()
    if ticker_upper in RESERVED_CONTROL_TOKENS:
        return "N/A"

    try:
        search_results = yf.Search(ticker_upper, max_results=5)
        quotes = getattr(search_results, "quotes", []) or []
        for quote in quotes:
            isin_val = quote.get("isin")
            if isin_val:
                return str(isin_val).upper()
    except Exception as exc:
        logger.debug("Ticker ISIN lookup failed for %s: %s", ticker_upper, exc)
    return "N/A"

def extract_security_identifier(
        query: str,
        holdings: Optional[Mapping[str, Mapping[str, Any]]] = None,
) -> tuple[Optional[str], Optional[str]]:
    """Extracts `(ticker, isin)` from a query string using ISIN patterns, explicit prefixes, or holdings."""
    query_upper = query.upper()

    isin_match = re.search(r"\b([A-Z]{2}[A-Z0-9]{9}[0-9])\b", query_upper)
    if isin_match:
        return None, isin_match.group(1)

    ticker_prefix_match = re.search(r"\bTICKER\s+([A-Z]{1,5})\b", query_upper)
    if ticker_prefix_match:
        extracted = ticker_prefix_match.group(1).upper()
        if extracted not in RESERVED_CONTROL_TOKENS:
            return extracted, None

    if holdings:
        for ticker in holdings.keys():
            sym = str(ticker).upper()
            if re.search(r"\b" + re.escape(sym) + r"\b", query_upper):
                return sym, None

    tokens = [
        token
        for token in re.findall(r"\b[A-Z]{2,5}\b", query_upper)
        if token not in EXCLUDED_QUERY_WORDS
    ]
    if tokens:
        return tokens[0], None

    return None, None

def find_matching_holding(
        ticker_query: Optional[str],
        isin_query: Optional[str],
        holdings: Mapping[str, Mapping[str, Any]],
) -> tuple[Optional[str], Optional[dict[str, Any]]]:
    """Finds a matching `(ticker, holding_dict)` entry by ISIN first, then by ticker."""
    if isin_query:
        isin_upper = isin_query.upper()
        for ticker, details in holdings.items():
            if str(details.get("isin", "")).upper() == isin_upper:
                return str(ticker), dict(details)

    if ticker_query:
        ticker_upper = ticker_query.upper()
        for ticker, details in holdings.items():
            if str(ticker).upper() == ticker_upper:
                return str(ticker), dict(details)

    return None, None