# tests/agent/test_valuation_agent.py

from deepeval import assert_test
from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCase, SingleTurnParams

from src.agent.valuation_agent import dcf_model_node, earnings_news_node

precision_metric = GEval(
    name="Valuation Analytical Precision",
    model="gpt-4o-mini",
    criteria="Ensure valuation metrics, P/E ratios, and SEC filing summaries match expected financial data.",
    evaluation_params=[SingleTurnParams.INPUT, SingleTurnParams.ACTUAL_OUTPUT],
    threshold=0.80,
)

def test_valuation_agent_nodes() -> None:
    """Test DCF assumptions and earnings news parsing nodes."""
    state = {
        "last_active_ticker": "AAPL",
        "retrieved_documents": [{"content": "AAPL reported Q3 net sales of $85.8 billion."}],
        "valuation_data": {},
    }

    dcf_res = dcf_model_node(state)
    assert dcf_res["current_step"] == "dcf_model_computed"
    assert dcf_res["valuation_data"]["assumptions"]["growth_rate"] == 0.08

    earnings_res = earnings_news_node(state)
    assert earnings_res["current_step"] == "earnings_news_parsed"
    assert earnings_res["valuation_data"]["doc_count"] == 1

def test_valuation_rag_output() -> None:
    test_case = LLMTestCase(
        input="What is Apple's Q3 revenue and valuation multiple?",
        actual_output=(
            "AAPL reported Q3 net sales of $85.8 billion with a trailing P/E ratio of 38.81 "
            "reflecting premium market pricing."
        ),
    )
    assert_test(test_case, [precision_metric])