import logging
from typing import Any

from langgraph.graph import END, START, StateGraph

from src.agent.market_agent import (
    market_data_node,
    run_market_analysis_node,
    sentiment_node,
    technical_indicator_node,
)
from src.agent.nodes.input_node import input_node
from src.agent.nodes.orchestrator_node import (
    analyze_query_node,
    route_intent,
    should_continue_market,
)
from src.agent.nodes.retrieval_node import retrieval_node
from src.agent.nodes.synthesis_node import synthesize_response_node
from src.agent.risk_agent import (
    compliance_guardrail_node,
    execution_order_node,
    portfolio_risk_node,
    tax_regulatory_node,
)
from src.agent.state import FinancialAssistantState
from src.agent.valuation_agent import (
    dcf_model_node,
    earnings_news_node,
    fundamentals_node,
)
from src.core.redis_client import checkpointer

logger = logging.getLogger(__name__)

GRAPH_NODES: list[tuple[str, Any]] = [
    ("process_input", input_node),
    ("analyze_query", analyze_query_node),
    ("retrieve_documents", retrieval_node),
    ("synthesize_response", synthesize_response_node),
    ("market_data", market_data_node),
    ("technical_indicators", technical_indicator_node),
    ("market_sentiment", sentiment_node),
    ("run_market_analysis", run_market_analysis_node),
    ("valuation_fundamentals", fundamentals_node),
    ("valuation_dcf", dcf_model_node),
    ("valuation_earnings", earnings_news_node),
    ("risk_portfolio", portfolio_risk_node),
    ("risk_tax", tax_regulatory_node),
    ("risk_execution", execution_order_node),
    ("risk_compliance", compliance_guardrail_node),
]

def create_financial_graph() -> Any:
    """Builds and compiles the multi-agent financial assistant LangGraph workflow."""
    logger.info("Compiling financial assistant LangGraph workflow...")
    workflow = StateGraph(FinancialAssistantState)

    for node_name, node_fn in GRAPH_NODES:
        workflow.add_node(node_name, node_fn)

    workflow.add_edge(START, "process_input")
    workflow.add_edge("process_input", "analyze_query")
    workflow.add_edge("analyze_query", "retrieve_documents")

    workflow.add_conditional_edges(
        "retrieve_documents",
        route_intent,
        {
            "market_domain": "market_data",
            "valuation_domain": "valuation_fundamentals",
            "risk_domain": "risk_portfolio",
        },
    )

    workflow.add_conditional_edges(
        "market_data",
        should_continue_market,
        {
            "skip_to_end": "synthesize_response",
            "continue_analysis": "technical_indicators",
        },
    )
    workflow.add_edge("technical_indicators", "market_sentiment")
    workflow.add_edge("market_sentiment", "run_market_analysis")
    workflow.add_edge("run_market_analysis", "synthesize_response")

    workflow.add_edge("valuation_fundamentals", "valuation_dcf")
    workflow.add_edge("valuation_dcf", "valuation_earnings")
    workflow.add_edge("valuation_earnings", "synthesize_response")

    workflow.add_edge("risk_portfolio", "risk_tax")
    workflow.add_edge("risk_tax", "risk_execution")
    workflow.add_edge("risk_execution", "risk_compliance")
    workflow.add_edge("risk_compliance", "synthesize_response")

    workflow.add_edge("synthesize_response", END)

    compiled_graph = workflow.compile(checkpointer=checkpointer)
    logger.info("Financial LangGraph workflow compiled successfully.")
    return compiled_graph

financial_graph = create_financial_graph()
app = financial_graph