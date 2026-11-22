# tests/rag/test_hybrid_retriever.py

from deepeval import assert_test
from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCase, SingleTurnParams
import pytest

from src.rag.hybrid_retriever import HybridRetriever

rag_precision_metric = GEval(
    name="RAG Grounding & Analytical Precision",
    model="gpt-4o-mini",
    criteria=(
        "Verify that the retrieved context and synthesized answer directly address "
        "the financial query using only grounded facts from the indexed filings/macro reports "
        "without cross-ticker contamination or hallucination."
    ),
    evaluation_steps=[
        "1. Verify the target entity (e.g., LLY, AAPL, MSFT, or MACRO) matches the query.",
        "2. Confirm numerical figures, percentages, and qualitative drivers match the retrieval context.",
        "3. Assign a score from 1 (hallucinated/wrong entity) to 5 (accurate and strictly grounded).",
    ],
    evaluation_params=[
        SingleTurnParams.INPUT,
        SingleTurnParams.ACTUAL_OUTPUT,
        SingleTurnParams.RETRIEVAL_CONTEXT,
    ],
    threshold=0.80,
)

@pytest.fixture
def sample_hybrid_retriever() -> HybridRetriever:
    """Provides a deterministic HybridRetriever seeded across revenue, risk/macro, and valuation docs."""
    sample_docs = [
        "LLY (Eli Lilly and Co.) Q3 revenue grew 20% YoY to $11.44B, driven by Mounjaro and Zepbound volume expansion, with non-GAAP EPS up 118%.",
        "AAPL (Apple Inc.) Q3 10-Q: Services revenue reached an all-time record of $24.21B, up 14.1% YoY, outpacing hardware growth.",
        "MSFT (Microsoft Corp.) Q3 operating margin expanded 210 bps YoY to 44.6%, driven by Azure cloud scale efficiencies and disciplined operating expense control.",
        "SEC Risk Factors (Multi-Constituent): Primary supply chain risks include single-source semiconductor packaging bottlenecks, geopolitical tariff exposure, and freight transit delays.",
        "MACRO Financial Report: Federal Reserve commentary indicates a higher-for-longer interest rate trajectory, pressuring commercial real estate (CRE) refinancing cap rates and regional bank office exposure.",
        "Q3 Multinational Earnings Summary: Foreign exchange headwinds created a 150-200 bps top-line revenue drag for US multinationals due to USD appreciation against the EUR and JPY.",
        "Balance Sheet & Liquidity Summary (MSFT/AAPL): Long-term debt maturities are laddered through 2034 with weighted-average coupons under 3.4%, backed by $65B+ in cash and marketable securities.",
        "CapEx & Infrastructure Guidance: Current FY capital expenditure guidelines represent a 28% increase over historical 3-year averages, heavily weighted toward AI data center compute capacity.",
        "Indexed Valuation Reports (DCF Methodology): Discounted cash flow models assume a terminal growth rate of 2.5% to 3.0% (aligned with long-run nominal GDP) and a WACC range of 8.2% to 9.1%.",
    ]
    sample_metadatas = [
        {"ticker": "LLY", "category": "revenue_earnings", "source": "LLY_10Q"},
        {"ticker": "AAPL", "category": "revenue_earnings", "source": "AAPL_10Q"},
        {"ticker": "MSFT", "category": "revenue_earnings", "source": "MSFT_10Q"},
        {"ticker": "MULTI", "category": "risk_macro", "source": "SEC_RISK_FACTORS"},
        {"ticker": "MACRO", "category": "risk_macro", "source": "FED_MACRO_NOTE"},
        {"ticker": "MULTI", "category": "risk_macro", "source": "Q3_FX_REPORT"},
        {"ticker": "MULTI", "category": "valuation_balance_sheet", "source": "BALANCE_SHEET_AUDIT"},
        {"ticker": "MULTI", "category": "valuation_balance_sheet", "source": "CAPEX_GUIDANCE"},
        {"ticker": "MULTI", "category": "valuation_balance_sheet", "source": "DCF_VALUATION_MODEL"},
    ]
    sample_ids = [f"doc_{i}" for i in range(1, 10)]

    return HybridRetriever(
        vector_store=None,
        documents=sample_docs,
        metadatas=sample_metadatas,
        ids=sample_ids,
    )

@pytest.mark.parametrize(
    "query,expected_ticker,expected_keyword",
    [
        ("What is Eli Lilly and Co's (LLY) recent revenue and earnings growth?", "LLY", "Mounjaro"),
        ("How did Apple's services revenue trend year-over-year in the latest 10-Q filing?", "AAPL", "24.21B"),
        ("What were the primary drivers of operating margin expansion for Microsoft last quarter?", "MSFT", "Azure"),
    ],
)
def test_rag_revenue_and_earnings_retrieval(
        sample_hybrid_retriever: HybridRetriever,
        query: str,
        expected_ticker: str,
        expected_keyword: str,
) -> None:
    results = sample_hybrid_retriever.search(query, top_k=1)
    assert len(results) > 0
    top_doc = results[0]["content"]
    assert expected_ticker in top_doc
    assert expected_keyword in top_doc

def test_rag_lly_growth_geval() -> None:
    context = [
        "LLY (Eli Lilly and Co.) Q3 revenue grew 20% YoY to $11.44B, driven by Mounjaro and Zepbound volume expansion, with non-GAAP EPS up 118%."
    ]
    test_case = LLMTestCase(
        input="What is Eli Lilly and Co's (LLY) recent revenue and earnings growth?",
        actual_output=(
            "Eli Lilly (LLY) reported 20% YoY revenue growth to $11.44 billion in Q3, propelled by "
            "strong demand for Mounjaro and Zepbound, alongside a 118% increase in non-GAAP EPS."
        ),
        retrieval_context=context,
    )
    assert_test(test_case, [rag_precision_metric])

@pytest.mark.parametrize(
    "query,expected_keyword",
    [
        ("What are the primary supply chain risk factors highlighted in the recent SEC filings?", "semiconductor"),
        ("How does the Federal Reserve's commentary on interest rate trajectories impact commercial real estate exposure?", "commercial real estate"),
        ("What foreign exchange headwinds did multinational constituents face in Q3?", "USD appreciation"),
    ],
)
def test_rag_risk_and_macro_retrieval(
        sample_hybrid_retriever: HybridRetriever,
        query: str,
        expected_keyword: str,
) -> None:
    results = sample_hybrid_retriever.search(query, top_k=1)
    assert len(results) > 0
    assert expected_keyword.lower() in results[0]["content"].lower()

def test_rag_fed_cre_macro_geval() -> None:
    context = [
        "MACRO Financial Report: Federal Reserve commentary indicates a higher-for-longer interest rate trajectory, pressuring commercial real estate (CRE) refinancing cap rates and regional bank office exposure."
    ]
    test_case = LLMTestCase(
        input="How does the Federal Reserve's commentary on interest rate trajectories impact commercial real estate exposure?",
        actual_output=(
            "According to the macro report, the Federal Reserve's higher-for-longer rate posture puts "
            "upward pressure on commercial real estate (CRE) refinancing cap rates and heightens credit "
            "exposure for regional banks holding office loans."
        ),
        retrieval_context=context,
    )
    assert_test(test_case, [rag_precision_metric])

@pytest.mark.parametrize(
    "query,expected_keyword",
    [
        ("What is the current breakdown of long-term debt maturities and liquidity reserves?", "2034"),
        ("How do the current capital expenditure guidelines compare to historical 3-year averages?", "28%"),
        ("What assumptions underpin the discounted cash flow (DCF) terminal growth rate in the indexed valuation reports?", "2.5%"),
    ],
)
def test_rag_valuation_and_balance_sheet_retrieval(
        sample_hybrid_retriever: HybridRetriever,
        query: str,
        expected_keyword: str,
) -> None:
    results = sample_hybrid_retriever.search(query, top_k=1)
    assert len(results) > 0
    assert expected_keyword in results[0]["content"]

def test_rag_dcf_assumptions_geval() -> None:
    context = [
        "Indexed Valuation Reports (DCF Methodology): Discounted cash flow models assume a terminal growth rate of 2.5% to 3.0% (aligned with long-run nominal GDP) and a WACC range of 8.2% to 9.1%."
    ]
    test_case = LLMTestCase(
        input="What assumptions underpin the discounted cash flow (DCF) terminal growth rate in the indexed valuation reports?",
        actual_output=(
            "The indexed DCF valuation models assume a terminal growth rate between 2.5% and 3.0%—"
            "benchmarked against long-run nominal GDP—paired with a WACC ranging from 8.2% to 9.1%."
        ),
        retrieval_context=context,
    )
    assert_test(test_case, [rag_precision_metric])
