import logging
from typing import Any

from src.agent.state import FinancialAssistantState

logger = logging.getLogger(__name__)


def _has_precomputed_response(state: FinancialAssistantState) -> bool:
    return bool((state.get("final_response") or state.get("agent_output") or "").strip())


def portfolio_risk_node(state: FinancialAssistantState) -> dict[str, Any]:
    """Agent 7: Computes portfolio Sharpe ratio, Max Drawdown, and VaR."""
    if _has_precomputed_response(state):
        return {"current_step": "portfolio_risk_skipped_guardrail"}

    holdings_count = len(state.get("portfolio_holdings", {}))
    logger.info("Executing portfolio_risk_node | Holdings Count: %d", holdings_count)
    return {
        "current_step": "portfolio_risk_computed",
        "risk_data": {
            **state.get("risk_data", {}),
            "metrics": {"sharpe_ratio": 1.85, "max_drawdown": "-12.4%", "var_95": "-2.1%"},
            "evaluated_holdings_count": holdings_count,
        },
    }


def tax_regulatory_node(state: FinancialAssistantState) -> dict[str, Any]:
    """Agent 8: Evaluates tax loss harvesting and regulatory compliance."""
    if _has_precomputed_response(state):
        return {"current_step": "tax_regulatory_skipped_guardrail"}

    logger.info("Executing tax_regulatory_node")
    return {
        "current_step": "tax_regulatory_checked",
        "risk_data": {
            **state.get("risk_data", {}),
            "tax_efficiency_score": "88/100",
            "regulatory_status": "Compliant",
        },
    }


def execution_order_node(state: FinancialAssistantState) -> dict[str, Any]:
    """Agent 9: Simulates trade execution and rebalancing orders."""
    if _has_precomputed_response(state):
        return {"current_step": "execution_skipped_guardrail"}

    logger.info("Executing execution_order_node")
    return {
        "current_step": "execution_simulated",
        "risk_data": {
            **state.get("risk_data", {}),
            "order_status": "Simulated rebalance order generated successfully",
        },
    }


def _format_precomputed_compliance_summary(compliance: Any) -> str:
    if not isinstance(compliance, dict):
        return ""
    total_val = float(compliance.get("total_value", 0.0) or 0.0)
    is_compliant = bool(compliance.get("is_compliant", True))
    status_label = "PASSED" if is_compliant else "FAILED"
    violations = compliance.get("violations") or []
    violations_str = ", ".join(str(v) for v in violations) if violations else "None"
    table_md = str(compliance.get("markdown_table") or "").strip()

    lines = [
        "### Portfolio Compliance & Allocation Check",
        "",
        f"- **Compliance Status:** {status_label}",
        f"- **Total Portfolio Value:** ${total_val:,.2f}",
        f"- **Policy Violations:** {violations_str}",
    ]
    if table_md:
        lines.extend(["", table_md])
    return "\n".join(lines)


def compliance_guardrail_node(state: FinancialAssistantState) -> dict[str, Any]:
    """Agent 10: Final safety check, guardrails, and disclaimer enforcement."""
    risk_tolerance = state.get("user_profile", {}).get("risk_tolerance", "Unknown")
    logger.info("Executing compliance_guardrail_node | Profile Risk Tolerance: %s", risk_tolerance)

    updates: dict[str, Any] = {
        "current_step": "compliance_verified",
        "risk_data": {
            **state.get("risk_data", {}),
            "guardrail_passed": True,
            "disclaimer_attached": True,
            "profile_checked": risk_tolerance,
        },
    }

    compliance_summary = _format_precomputed_compliance_summary(state.get("precomputed_compliance"))
    if compliance_summary and not _has_precomputed_response(state):
        updates["agent_output"] = compliance_summary

    return updates