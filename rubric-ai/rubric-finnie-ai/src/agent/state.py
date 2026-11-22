from typing import Any, Optional, TypedDict

class FinancialAssistantState(TypedDict):
    """Global state schema for multi-agent financial assistant orchestration."""

    user_query: str
    session_id: str

    active_user_id: str
    user_profile: dict[str, Any]
    portfolio_holdings: dict[str, Any]

    messages: list[dict[str, Any]]

    retrieved_documents: list[dict[str, Any]]
    analysis_results: dict[str, Any]

    market_data: dict[str, Any]
    valuation_data: dict[str, Any]
    risk_data: dict[str, Any]

    next_domain: str
    current_step: str
    errors: list[str]
    final_response: str
    agent_output: Optional[str]

    last_active_ticker: Optional[str]
    full_historical_closes: Optional[dict[str, float]]