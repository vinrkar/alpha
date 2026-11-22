# tests/agent/test_state.py

from src.agent.state import FinancialAssistantState

REQUIRED_STATE_KEYS: set[str] = {
    "user_query",
    "session_id",
    "active_user_id",
    "user_profile",
    "portfolio_holdings",
    "messages",
    "retrieved_documents",
    "analysis_results",
    "market_data",
    "valuation_data",
    "risk_data",
    "next_domain",
    "current_step",
    "errors",
    "final_response",
    "agent_output",
    "last_active_ticker",
    "full_historical_closes",
}

def test_financial_assistant_state_structure() -> None:
    """Verify that FinancialAssistantState TypedDict contains all required keys."""
    annotations = FinancialAssistantState.__annotations__
    for key in REQUIRED_STATE_KEYS:
        assert key in annotations, f"Missing required state key: {key}"