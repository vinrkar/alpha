# src/agent/nodes/input_node.py

import logging
import re
from typing import Any

from langchain_core.runnables import RunnableConfig

from src.agent.state import FinancialAssistantState
from src.database.repository import get_all_user_profiles
from src.utils.resolution import (
    IGNORED_NAME_WORDS,
    RESERVED_CONTROL_TOKENS,
    extract_security_identifier,
    resolve_ticker_from_isin,
)

logger = logging.getLogger(__name__)

def _fallback_ticker_from_history(messages: list[dict[str, Any]]) -> str | None:
    for msg in reversed(messages[:-1]):
        content = (msg.get("content") or "").upper()
        tokens = [
            token
            for token in re.findall(r"\b[A-Z]{1,5}\b", content)
            if token not in IGNORED_NAME_WORDS and token not in RESERVED_CONTROL_TOKENS
        ]
        if tokens:
            return tokens[0]
    return None

def input_node(state: FinancialAssistantState, config: RunnableConfig) -> dict[str, Any]:
    profiles = get_all_user_profiles()
    default_profile_id = next(iter(profiles.keys()), "default_user")

    query = state.get("user_query", "")
    user_id = state.get("active_user_id") or default_profile_id
    profile_data = profiles.get(user_id, profiles.get(default_profile_id, {}))
    persisted_ticker = state.get("last_active_ticker")

    existing_messages = list(state.get("messages", [])[-10:])
    existing_messages.append({"role": "user", "content": query})

    holdings = profile_data.get("holdings", {})
    ticker_extracted, isin_extracted = extract_security_identifier(query, holdings)

    resolved_ticker = persisted_ticker
    if ticker_extracted and ticker_extracted not in RESERVED_CONTROL_TOKENS:
        resolved_ticker = ticker_extracted
    elif isin_extracted:
        resolved_ticker = resolve_ticker_from_isin(isin_extracted)
    elif not resolved_ticker and existing_messages:
        resolved_ticker = _fallback_ticker_from_history(existing_messages)

    return {
        "current_step": "input_processed",
        "active_user_id": user_id,
        "user_profile": {
            "name": profile_data.get("name", "Valued Client"),
            "risk_tolerance": profile_data.get("risk_tolerance", "Moderate"),
            "investment_horizon": profile_data.get("investment_horizon", "Long-term"),
        },
        "portfolio_holdings": holdings,
        "messages": existing_messages,
        "last_active_ticker": resolved_ticker,
        "agent_output": None,
        "final_response": None,
    }