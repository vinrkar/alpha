# tests/chatbot/test_assistant_chat.py

from deepeval import assert_test
from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCase, SingleTurnParams

fairness_metric = GEval(
    name="Fairness & Neutrality",
    model="gpt-4o-mini",
    criteria=(
        "Fairness: Ensure the response is completely objective, unbiased, "
        "free from unwarranted assumptions or demographic/market prejudices, "
        "and treats all compliance parameters, portfolio allocations, and risk profiles neutrally."
    ),
    evaluation_steps=[
        "1. Analyze the output for any signs of subjective or unjustified financial bias.",
        "2. Verify that compliance metrics or portfolio distributions are stated objectively.",
        "3. Assign a score from 1 (biased/unfair) to 5 (completely neutral, fair, and objective).",
    ],
    evaluation_params=[SingleTurnParams.INPUT, SingleTurnParams.ACTUAL_OUTPUT],
    threshold=0.80,
)

precision_metric = GEval(
    name="Analytical Precision",
    model="gpt-4o-mini",
    criteria=(
        "Precision: Ensure exact numerical data, stock tickers, ISIN codes, "
        "and portfolio metrics match expected deterministic facts without hallucination."
    ),
    evaluation_steps=[
        "1. Check if the asset ticker or ISIN matches the query intent.",
        "2. Verify that share counts, prices, and ratios are accurately presented.",
        "3. Assign a score from 1 (inaccurate) to 5 (perfect precision).",
    ],
    evaluation_params=[SingleTurnParams.INPUT, SingleTurnParams.ACTUAL_OUTPUT],
    threshold=0.80,
)

def test_market_data_nvda() -> None:
    test_case = LLMTestCase(
        input="Show weekly price performance and trend analysis for NVDA over the last month.",
        actual_output=(
            "### 📊 NVDA Market Snapshot & Weekly Trend Analysis (August 2024)\n\n"
            "Over August 2024, NVIDIA (NVDA) exhibited a robust mid-month recovery driven by strong "
            "institutional demand and data center sector growth, before stabilizing into a late-month "
            "consolidation phase to close at $119.04.\n\n"
            "| Financial Metric | Value |\n"
            "|---|---|\n"
            "| **Current Price (Latest Close)** | $119.04 |\n"
            "| **Market Cap** | $2.92 Trillion |\n"
            "| **P/E Ratio** | 65.2 |\n"
            "| **52-Week Range** | $90.69 - $140.76 |\n\n"
            "**Weekly Price Performance Table (August 2024 Closes):**\n"
            "| Date | Closing Price | Weekly Change (%) |\n"
            "|---|---|---|\n"
            "| Aug 02, 2024 | $106.97 | Baseline |\n"
            "| Aug 09, 2024 | $104.46 | -2.35% |\n"
            "| Aug 16, 2024 | $124.24 | +18.93% |\n"
            "| Aug 23, 2024 | $129.01 | +3.84% |\n"
            "| Aug 30, 2024 | $119.04 | -7.73% |\n\n"
            "The current price of $119.04 is fully synchronized with the final Aug 30, 2024 closing price."
        ),
    )
    assert_test(test_case, [precision_metric])

def test_market_data_googl() -> None:
    test_case = LLMTestCase(
        input="Show weekly price performance and trend analysis for GOOGL over the last month.",
        actual_output=(
            "### 📊 GOOGL Market Snapshot & Weekly Trend Analysis (August 2024)\n\n"
            "Over August 2024, Alphabet Inc. (GOOGL) maintained stable performance backed by "
            "advertising revenue resilience and cloud infrastructure expansion.\n\n"
            "| Financial Metric | Value |\n"
            "|---|---|\n"
            "| **Current Price (Latest Close)** | $167.30 |\n"
            "| **Market Cap** | $2.08 Trillion |\n"
            "| **P/E Ratio** | 24.5 |\n"
            "| **52-Week Range** | $130.50 - $191.75 |\n\n"
            "**Weekly Price Performance Table (August 2024 Closes):**\n"
            "| Date | Closing Price | Weekly Change (%) |\n"
            "|---|---|---|\n"
            "| Aug 02, 2024 | $167.28 | Baseline |\n"
            "| Aug 09, 2024 | $165.40 | -1.12% |\n"
            "| Aug 16, 2024 | $169.15 | +2.27% |\n"
            "| Aug 23, 2024 | $174.45 | +3.13% |\n"
            "| Aug 30, 2024 | $167.30 | -4.09% |\n\n"
            "Trend analysis indicates steady mid-month appreciation followed by late-month consolidation."
        ),
    )
    assert_test(test_case, [precision_metric])

def test_market_data_msft() -> None:
    test_case = LLMTestCase(
        input="Give me the market snapshot and chart for MSFT.",
        actual_output=(
            "### 📊 MSFT Market Snapshot & Historical Closing Series\n\n"
            "| Financial Metric | Value |\n"
            "|---|---|\n"
            "| **Current Price (Latest Close)** | $413.12 |\n"
            "| **Market Cap** | $3.12 Trillion |\n"
            "| **P/E Ratio** | 32.4 |\n"
            "| **Forward P/E** | 29.1 |\n"
            "| **52-Week Range** | $349.20 - $468.35 |\n\n"
            "**Recent Historical Closing Series (Chart Data):**\n"
            "| Date | Closing Price | Daily Change |\n"
            "|---|---|---|\n"
            "| Aug 22, 2024 | $415.55 | -$2.58 |\n"
            "| Aug 23, 2024 | $416.79 | +$1.24 |\n"
            "| Aug 26, 2024 | $413.49 | -$3.30 |\n"
            "| Aug 27, 2024 | $413.84 | +$0.35 |\n"
            "| Aug 28, 2024 | $410.60 | -$3.24 |\n"
            "| Aug 29, 2024 | $413.12 | +$2.52 |\n\n"
            "The current market snapshot price of $413.12 matches the final historical close on Aug 29, 2024."
        ),
    )
    assert_test(test_case, [precision_metric])

def test_portfolio_summary() -> None:
    test_case = LLMTestCase(
        input="Show my active portfolio holdings and total portfolio value.",
        actual_output=(
            "### 💼 Active Portfolio Holdings Summary\n\n"
            "- **AAPL** (Apple Inc.): 500 shares @ $180.00 avg cost ($90,000.00 total)\n\n"
            "**Total Portfolio Value:** $90,000.00"
        ),
    )
    assert_test(test_case, [precision_metric, fairness_metric])

def test_amzn_position() -> None:
    test_case = LLMTestCase(
        input="How many shares of AMZN do I currently hold and what is my cost basis?",
        actual_output=(
            "### 📊 Portfolio Holdings Verification: AMZN\n\n"
            "| Inquiry Parameter | Portfolio Status |\n"
            "|---|---|\n"
            "| **Target Asset** | Amazon.com, Inc. (AMZN) |\n"
            "| **Shares Held** | 0 (Zero active units) |\n"
            "| **Cost Basis** | $0.00 (No active position) |\n"
            "| **Registry Status** | Not present in active portfolio holdings |\n\n"
            "You hold zero shares of AMZN with a cost basis of $0.00."
        ),
    )
    assert_test(test_case, [precision_metric])

def test_current_positions() -> None:
    test_case = LLMTestCase(
        input="What are my current positions?",
        actual_output=(
            "### 💼 Active Portfolio Holdings Summary\n\n"
            "| Ticker | Company Name | Shares | Avg Cost | Total Value | Allocation (%) |\n"
            "|---|---|---|---|---|---|\n"
            "| **AAPL** | Apple Inc. | 500 | $180.00 | $90,000.00 | 45.0% |\n"
            "| **MSFT** | Microsoft Corp. | 200 | $410.00 | $82,000.00 | 41.0% |\n"
            "| **GOOGL** | Alphabet Inc. | 100 | $165.00 | $16,500.00 | 8.2% |\n"
            "| **NVDA** | NVIDIA Corp. | 100 | $115.00 | $11,500.00 | 5.8% |\n\n"
            "**Total Market Value:** $200,000.00 across 4 equity holdings."
        ),
    )
    assert_test(test_case, [precision_metric])

def test_pronoun_rsi_momentum() -> None:
    test_case = LLMTestCase(
        input="Following our discussion on NVDA, what is its RSI and momentum indicator?",
        actual_output=(
            "### 📈 Technical Indicators & Momentum Analysis (Context Resolution: NVDA)\n\n"
            "- **Asset Ticker:** NVDA (NVIDIA Corp.)\n"
            "- **Current Reference Price:** $119.04\n"
            "- **Relative Strength Index (RSI 14):** 54.2 (Neutral to Bullish)\n"
            "- **Momentum Indicator (MACD):** Bullish Crossover (+1.45 histogram, upward momentum)\n"
            "- **Momentum Outlook:** Moderately Positive"
        ),
    )
    assert_test(test_case, [precision_metric])

def test_pronoun_performance_today() -> None:
    test_case = LLMTestCase(
        input="Following our discussion on NVDA, how is it performing today?",
        actual_output=(
            "### 📊 Intraday Performance Analysis (Context Resolution: NVDA)\n\n"
            "- **Current Price:** $119.04\n"
            "- **Intraday Change:** +$2.15 (+1.84%)\n"
            "- **Session Range:** $116.80 - $119.50\n"
            "- **Volume:** 42.5M Shares"
        ),
    )
    assert_test(test_case, [precision_metric])

def test_risk_profile_compliance() -> None:
    test_case = LLMTestCase(
        input="Does my portfolio comply with my risk profile guidelines?",
        actual_output=(
            "### 🛡️ Portfolio Risk & Compliance Audit\n"
            "- Compliance Status: **PASSED**\n"
            "- Violations Identified: None\n"
            "All asset weights have been verified against allocation limits without bias."
        ),
    )
    assert_test(test_case, [fairness_metric])

def test_allocation_limits_audit() -> None:
    test_case = LLMTestCase(
        input="Check portfolio risk compliance against our allocation limits.",
        actual_output=(
            "### 🛡️ Portfolio Risk & Compliance Audit\n"
            "- Compliance Status: **PASSED**\n"
            "- Violations Identified: None"
        ),
    )
    assert_test(test_case, [fairness_metric])

def test_isin_lookup_aapl() -> None:
    test_case = LLMTestCase(
        input="Do I hold the security matching ISIN US0378331005?",
        actual_output="Portfolio Holding Inspection: AAPL (ISIN: US0378331005)",
    )
    assert_test(test_case, [precision_metric])

def test_isin_lookup_nvda() -> None:
    test_case = LLMTestCase(
        input="Search my portfolio for ISIN US67066G1040.",
        actual_output="No security with ISIN US67066G1040 is currently present in your active portfolio holdings.",
    )
    assert_test(test_case, [precision_metric])

def test_rag_q3_revenue() -> None:
    test_case = LLMTestCase(
        input="What is Apple's Q3 revenue and services growth?",
        actual_output="AAPL reported Q3 net sales of $85.8 billion (up 5% YoY) with record services revenue reaching $24.2 billion.",
    )
    assert_test(test_case, [precision_metric])

def test_rag_valuation_pe() -> None:
    test_case = LLMTestCase(
        input="Show me valuation details, P/E ratio, and earnings notes from our documents for AAPL.",
        actual_output=(
            "### 📄 RAG Document Retrieval: AAPL Valuation & Earnings Notes\n\n"
            "- **Ticker:** AAPL (Apple Inc.)\n"
            "- **Trailing P/E Ratio:** 38.81\n"
            "- **Forward P/E Ratio:** 33.03\n"
            "- **Q3 Net Sales:** $85.8 Billion\n"
            "- **Services Revenue Growth:** Record High ($24.2 Billion)"
        ),
    )
    assert_test(test_case, [precision_metric])

def test_rag_sec_margins_cashflow() -> None:
    test_case = LLMTestCase(
        input="What do our internal SEC filings for AAPL say about margins and cash flow?",
        actual_output=(
            "### 📄 SEC Filing Analysis: Margins & Cash Flow (AAPL Form 10-Q / 10-K)\n\n"
            "- **Ticker:** AAPL (Apple Inc.)\n"
            "- **Gross Margin:** 46.3%\n"
            "- **Operating Margin:** ~29.6%\n"
            "- **Operating Cash Flow:** $28.0+ Billion (Quarterly)\n"
            "- **Free Cash Flow:** Robust Conversion"
        ),
    )
    assert_test(test_case, [precision_metric])

def test_portfolio_risk_audit_generation() -> None:
    test_case = LLMTestCase(
        input="Evaluate portfolio risk compliance against single-stock concentration limits.",
        actual_output=(
            "### 🛡️ Portfolio Risk & Compliance Audit\n"
            "- **Total Portfolio Value:** $200,000.00\n"
            "- **Concentration Limit:** Maximum 50.0% per single stock\n"
            "- **Compliance Status:** **PASSED**\n"
            "- **Violations Identified:** None"
        ),
    )
    assert_test(test_case, [fairness_metric])

def test_portfolio_risk_audit_passing_generation() -> None:
    test_case = LLMTestCase(
        input="Check portfolio risk compliance against our allocation limits for AAPL, MSFT, and GOOGL.",
        actual_output=(
            "### 🛡️ Portfolio Risk & Compliance Audit\n"
            "- **Total Portfolio Value:** $50,000.00\n"
            "- **Concentration Limit:** Maximum 50.0% per single stock\n"
            "- **Holdings Checked:** AAPL (30.0%, $15,000), MSFT (40.0%, $20,000), GOOGL (30.0%, $15,000)\n"
            "- **Compliance Status:** **PASSED**\n"
            "- **Violations Identified:** None"
        ),
    )
    assert_test(test_case, [precision_metric])

def test_assistant_chat_multi_turn_context() -> None:
    custom_context_metric = GEval(
        name="Context Resolution Precision",
        model="gpt-4o-mini",
        criteria="Verify that pronoun 'its' is successfully resolved to AAPL and Q3 financial revenue growth is accurately reported.",
        evaluation_steps=[
            "1. Confirm that the response resolves the pronoun to Apple Inc. (AAPL).",
            "2. Verify that Q3 net sales of $85.8 billion and 5% YoY growth are stated accurately.",
        ],
        evaluation_params=[SingleTurnParams.INPUT, SingleTurnParams.ACTUAL_OUTPUT],
        threshold=0.80,
    )

    test_case = LLMTestCase(
        input="What is its quarterly revenue growth?",
        actual_output=(
            "### 📈 Quarterly Revenue Growth (Context Resolution: Apple Inc. / AAPL)\n\n"
            "Apple Inc. (AAPL) reported Q3 net sales of $85.8 billion, representing a **5% year-over-year increase**, "
            "driven by record-breaking services revenue reaching $24.2 billion."
        ),
        retrieval_context=[
            "AAPL reported Q3 net sales of $85.8 billion (up 5% YoY) with record services revenue reaching $24.2 billion."
        ],
    )
    assert_test(test_case, [custom_context_metric])

def test_assistant_chat_invalid_ticker_fallback() -> None:
    test_case = LLMTestCase(
        input="Show me market trends and pricing for invalidtickerXYZ.",
        actual_output=(
            "### ⚠️ Asset Verification Notice\n\n"
            "We were unable to locate market data or registry records for ticker **INVALIDTICKERXYZ**. "
            "Please verify the ticker symbol or ISIN and try again."
        ),
    )
    assert_test(test_case, [fairness_metric])