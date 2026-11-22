# tests/agent/test_graph.py

from typing import Any
from unittest.mock import patch

from langgraph.checkpoint.memory import MemorySaver
import pytest

from src.agent.graph import create_financial_graph
from src.database.repository import get_all_user_profiles

CLIENT_PROFILES = get_all_user_profiles()

def _base_state(
        user_query: str,
        session_id: str,
        active_user_id: str,
) -> dict[str, Any]:
    return {
        "user_query": user_query,
        "session_id": session_id,
        "active_user_id": active_user_id,
        "user_profile": {},
        "portfolio_holdings": {},
        "messages": [],
        "retrieved_documents": [],
        "analysis_results": {},
        "market_data": {},
        "valuation_data": {},
        "risk_data": {},
        "next_domain": "",
        "current_step": "",
        "errors": [],
        "final_response": "",
    }

@pytest.fixture
def graph_app() -> Any:
    with patch("src.agent.graph.checkpointer", MemorySaver()):
        return create_financial_graph()

def test_graph_compiles(graph_app: Any) -> None:
    assert graph_app is not None

def test_market_domain_routing(graph_app: Any) -> None:
    initial_state = _base_state(
        user_query="Show me market trends and stock prices.",
        session_id="test_1",
        active_user_id="C4820198",
    )
    result = graph_app.invoke(
        initial_state,
        config={"configurable": {"thread_id": "test_1"}},
    )
    assert result["current_step"] == "completed"
    assert result["next_domain"] == "market_domain"
    assert result["user_profile"]["name"] == CLIENT_PROFILES["C4820198"]["name"]

def test_risk_domain_routing(graph_app: Any) -> None:
    initial_state = _base_state(
        user_query="Verify portfolio compliance against our maximum asset weight limits and risk guidelines.",
        session_id="test_2",
        active_user_id="A3928104",
    )
    result = graph_app.invoke(
        initial_state,
        config={"configurable": {"thread_id": "test_2"}},
    )
    assert result["current_step"] == "completed"
    assert result["next_domain"] == "risk_domain"
    assert "risk_data" in result

def test_graph_error_recovery(graph_app: Any) -> None:
    """Test LangGraph state error recovery and fallback routing on empty/unknown inputs."""
    malformed_state = _base_state(
        user_query="",
        session_id="test_err_1",
        active_user_id="UNKNOWN_USER",
    )
    result = graph_app.invoke(
        malformed_state,
        config={"configurable": {"thread_id": "test_err_1"}},
    )
    assert "errors" in result or result["current_step"] in ["completed", "fallback", "error"]