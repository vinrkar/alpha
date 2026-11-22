# tests/agent/test_market_intelligence.py

from deepeval import assert_test
from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCase, SingleTurnParams

def _build_geval_metric(
        name: str,
        criteria: str,
        steps: list[str],
        threshold: float = 0.85,
) -> GEval:
    return GEval(
        name=name,
        model="gpt-4o-mini",
        criteria=criteria,
        evaluation_steps=steps,
        evaluation_params=[SingleTurnParams.INPUT, SingleTurnParams.ACTUAL_OUTPUT],
        threshold=threshold,
    )

aapl_precision_metric = _build_geval_metric(
    name="AAPL Snapshot Precision",
    criteria="Verify AAPL market snapshot includes correct valuation rows and numbers.",
    steps=[
        "1. Check that asset ticker (AAPL) is present.",
        "2. Verify markdown table contains Current Price, Market Cap, P/E Ratio, Forward P/E, and 52-Week Range.",
        "3. Confirm numerical values match the fixture.",
    ],
)

tsla_trend_precision_metric = _build_geval_metric(
    name="TSLA Trend Precision",
    criteria="Verify TSLA trend output includes current price, valuation metrics, and a chronological date-close table.",
    steps=[
        "1. Check that asset ticker (TSLA) is present.",
        "2. Verify presence of current valuation metrics and a chronological date/closing price table.",
        "3. Confirm trend summary aligns with data.",
    ],
)

sector_comparison_precision_metric = _build_geval_metric(
    name="Sector Comparison Precision",
    criteria="Verify multi-asset sector comparison contains multi-row matrix for MSFT, GOOGL, and NVDA.",
    steps=[
        "1. Check that all requested tickers (MSFT, GOOGL, NVDA) are present in the comparison matrix.",
        "2. Verify columns include Ticker, Company Name, Share Price, Market Cap, and P/E Ratio.",
        "3. Confirm sector takeaway correctly references matrix data.",
    ],
)

leaderboard_precision_metric = _build_geval_metric(
    name="Leaderboard & Technical Precision",
    criteria="Verify real-time market intelligence leaderboard includes price, volume, RSI, MACD, and sentiment indicators.",
    steps=[
        "1. Check that the asset ticker (LLY) and current price are present.",
        "2. Verify presence of technical indicators including RSI, MACD, and sentiment score.",
        "3. Confirm numerical accuracy and structured table formatting.",
    ],
)

def test_market_intelligence_aapl_snapshot() -> None:
    """Test Market Intelligence: AAPL Market Snapshot and Valuation Metrics."""
    test_case = LLMTestCase(
        input="Provide a market intelligence snapshot and valuation breakdown for AAPL.",
        actual_output=(
            "### 📊 AAPL Market Intelligence & Valuation Snapshot\n\n"
            "| Financial Metric | Value |\n"
            "|---|---|\n"
            "| **Current Price (Latest Close)** | $225.30 |\n"
            "| **Market Cap** | $3.45 Trillion |\n"
            "| **P/E Ratio** | 34.2 |\n"
            "| **Forward P/E** | 29.8 |\n"
            "| **52-Week Range** | $164.08 - $237.23 |\n\n"
            "**Intelligence Summary:**\n"
            "Apple Inc. (AAPL) trades near the upper end of its 52-week range, supported by "
            "resilient hardware replacement cycles and steady expansion in its high-margin Services segment."
        ),
    )
    assert_test(test_case, [aapl_precision_metric])

def test_market_intelligence_tsla_weekly_trend() -> None:
    """Test Market Intelligence: TSLA Weekly Closing Performance & Trend Analysis."""
    test_case = LLMTestCase(
        input="Show weekly price performance and trend analysis for TSLA over the last month.",
        actual_output=(
            "### 📊 TSLA Market Intelligence & Weekly Trend Analysis\n\n"
            "Tesla, Inc. (TSLA) closed at $215.40 with valuation metrics as follows:\n\n"
            "| Financial Metric | Value |\n"
            "|---|---|\n"
            "| **Current Price (Latest Close)** | $215.40 |\n"
            "| **Market Cap** | $685.2 Billion |\n"
            "| **P/E Ratio** | 62.4 |\n"
            "| **52-Week Range** | $138.80 - $271.00 |\n\n"
            "**Trailing Month Closes:**\n"
            "| Date | Closing Price |\n"
            "|---|---|\n"
            "| Aug 02, 2024 | $205.10 |\n"
            "| Aug 09, 2024 | $222.50 |\n"
            "| Aug 16, 2024 | $218.30 |\n"
            "| Aug 23, 2024 | $215.40 |\n\n"
            "**Trend Summary:**\n"
            "The pricing data confirms a strong mid-month rally followed by minor profit-taking "
            "and consolidation near the $215 support level."
        ),
    )
    assert_test(test_case, [tsla_trend_precision_metric])

def test_market_intelligence_sector_comparison() -> None:
    """Test Market Intelligence: Multi-Asset Mega-Cap Tech Comparison."""
    test_case = LLMTestCase(
        input="Compare market metrics for MSFT, GOOGL, and NVDA.",
        actual_output=(
            "### 📊 Mega-Cap Technology Sector Intelligence Matrix\n\n"
            "| Ticker | Company Name | Share Price | Market Cap | P/E Ratio |\n"
            "|---|---|---|---|---|\n"
            "| **MSFT** | Microsoft Corp. | $413.12 | $3.12 Trillion | 32.4 |\n"
            "| **GOOGL** | Alphabet Inc. | $167.30 | $2.08 Trillion | 24.5 |\n"
            "| **NVDA** | NVIDIA Corp. | $119.04 | $2.92 Trillion | 65.2 |\n\n"
            "**Sector Takeaway:**\n"
            "NVIDIA carries the highest earnings multiple (P/E 65.2) reflecting aggressive growth "
            "expectations tied to AI hardware infrastructure, while Alphabet offers the lowest "
            "relative valuation multiple (P/E 24.5) among the group."
        ),
    )
    assert_test(test_case, [sector_comparison_precision_metric])

def test_market_intelligence_live_leaderboard() -> None:
    """Test Market Intelligence: Real-Time Leaderboard & Technical Indicators."""
    test_case = LLMTestCase(
        input="Show me the live market intelligence leaderboard and technical indicators for Eli Lilly (LLY).",
        actual_output=(
            "### 📊 Live Market Intelligence Leaderboard: LLY\n\n"
            "| Ticker | Price ($) | Change (%) | Volume | Mkt Cap | P/E | RSI | MACD | Sentiment |\n"
            "|---|---|---|---|---|---|---|---|---|\n"
            "| **LLY** | $749.00 | +0.25% | 425.1K | $711.07B | 41.20 | 51.74 | Neutral | Neutral |\n\n"
            "**Technical & Sentiment Summary:**\n"
            "Eli Lilly (LLY) exhibits stable volume with an RSI of 51.74 indicating a neutral momentum "
            "baseline, backed by steady live streaming telemetry from exchange feeds."
        ),
    )
    assert_test(test_case, [leaderboard_precision_metric])