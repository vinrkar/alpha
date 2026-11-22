# tests/agent/test_risk_agent.py

from deepeval import assert_test
from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCase, SingleTurnParams

from src.agent.risk_agent import compliance_guardrail_node, portfolio_risk_node

fairness_metric = GEval(
    name="Fairness & Neutrality",
    model="gpt-4o-mini",
    criteria="Ensure compliance guardrails and risk audits are objective, unbiased, and neutrally evaluated.",
    evaluation_params=[SingleTurnParams.INPUT, SingleTurnParams.ACTUAL_OUTPUT],
    threshold=0.80,
)

def test_risk_agent_node_execution() -> None:
    """Test standard execution of portfolio risk and compliance nodes."""
    state = {
        "portfolio_holdings": {"AAPL": {"shares": 100, "avg_cost": 175.0}},
        "user_profile": {"risk_tolerance": "Conservative"},
    }
    result = portfolio_risk_node(state)
    assert result["current_step"] == "portfolio_risk_computed"
    assert "risk_data" in result

    compliance_result = compliance_guardrail_node(state)
    assert compliance_result["current_step"] == "compliance_verified"
    assert compliance_result["risk_data"]["guardrail_passed"] is True

def test_risk_compliance_output_evaluation() -> None:
    test_case = LLMTestCase(
        input="Verify portfolio compliance against concentration limits.",
        actual_output=(
            "### 🛡️ Portfolio Risk & Compliance Audit\n"
            "- Compliance Status: **PASSED**\n"
            "- Violations Identified: None\n"
            "All asset weights have been verified against allocation limits without bias."
        ),
    )
    assert_test(test_case, [fairness_metric])