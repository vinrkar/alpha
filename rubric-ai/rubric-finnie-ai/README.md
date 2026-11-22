# 📈 Rubric Finnie AI – Multi-Agent Financial Assistant

Financial intelligence, valuation modeling, portfolio analytics, and risk compliance platform powered by a **10-agent** LangGraph workflow, Hybrid RAG (ChromaDB + BM25), Model Context Protocol (MCP), Redis semantic caching, FastAPI, and a multi-view Streamlit dashboard.

---

## 🎯 Problem Statement

Financial literacy remains a significant barrier for everyday investors due to complex financial jargon, fragmented research tools, and uncertainty around risk and suitability. **Rubric Finnie AI** addresses this gap by combining **10** specialized agents, live market data (`yfinance`), and Hybrid RAG (ChromaDB + BM25) to deliver clear, grounded explanations, valuation modeling, and risk suitability guardrails—while maintaining clear educational disclaimers rather than acting as a licensed financial advisor.

---

## 🧠 AI Models, Caching, & Storage Architecture

* **Dual-Model Setup (Cloud + Desktop):** Combines **OpenAI** cloud models (`gpt-4o`, `gpt-4o-mini`, `text-embedding-3-small`) with local **Ollama** (`qwen2.5:1.5b`) running on desktop for flexible inference and local execution.
* **Semantic Caching & Prompt Caching:** Uses **Redis** (`semcache*` in `src/core/redis_client.py`) for scope- and date-aware semantic caching, paired with structured system and agent prompts (`src/prompts/system_prompts.py`, `src/prompts/agent_prompts.py`) designed for consistent instructions and prompt caching efficiency.
* **Vector DB & Hybrid RAG:** Pairs **ChromaDB** dense vector search (`src/rag/vector_store.py`) with **BM25** sparse lexical retrieval (`src/rag/bm25_retriever.py`) inside `src/rag/hybrid_retriever.py`.
* **SQLite & Session Persistence:** Uses **SQLite** (`src/database/`) for investor/staff profiles and repository access, alongside Redis and session persistence (`data/sessions/`) for conversation state and history.
* **MCP Integration:** Exposes and consumes financial capabilities via the Model Context Protocol server and client (`src/mcp/financial_server.py`, `src/mcp/financial_client.py`).

---

## 🤖 Agent Architecture (10 Agents)

### Market Agents (`src/agent/market_agent.py`)
1. 📡 **Market Data Agent (`market_data_node`):** Handles market data lookups, portfolio lookups, and RAG valuation searches.
2. 📈 **Technical Indicator Agent (`technical_indicator_node`):** Computes dynamic technical momentum indicators (such as RSI-14 and MACD signal) when an active ticker is present.
3. 💬 **Sentiment Agent (`sentiment_node`):** Evaluates available sentiment context without fabricating static scores.

### Valuation Agents (`src/agent/valuation_agent.py`)
4. 📊 **Fundamentals Agent (`fundamentals_node`):** Evaluates P/E, forward P/E, market cap, and financial statement metrics dynamically.
5. 🧮 **DCF Model Agent (`dcf_model_node`):** Computes Discounted Cash Flow (DCF) valuation assumptions.
6. 📰 **Earnings & Filings Agent (`earnings_news_node`):** Parses SEC filings, earnings reports, and transcripts from retrieved documents.

### Risk & Compliance Agents (`src/agent/risk_agent.py`)
7. 🛡️ **Portfolio Risk Agent (`portfolio_risk_node`):** Evaluates portfolio Sharpe ratio, Max Drawdown, and VaR.
8. 🧾 **Tax & Regulatory Agent (`tax_regulatory_node`):** Checks tax-loss harvesting and regulatory compliance status.
9. ⚙️ **Execution Order Agent (`execution_order_node`):** Simulates trade execution and rebalancing orders (paired with `src/services/trading_service.py` and the Order Execution tab).
10. 🔒 **Compliance Guardrail Agent (`compliance_guardrail_node`):** Enforces final safety checks, guardrails, and disclaimer attachment.

### Orchestration & Synthesis (`src/agent/graph.py`)
1. 📥 **Input Node (`process_input` / `input_node.py`):** Normalizes incoming queries and initializes session/user context over `FinancialAssistantState`.
2. 🧭 **Orchestrator Node (`analyze_query` / `orchestrator_node.py`):** Analyzes intent and routes requests across market, valuation, and risk domains.
3. 🔎 **Retrieval Node (`retrieve_documents` / `retrieval_node.py`):** Runs Hybrid RAG (ChromaDB + BM25) retrieval to ground domain agents.
4. 📊 **Market Synthesis Node (`run_market_analysis` / `market_node.py`):** Formats market findings, indicators, and historical price tables.
5. 🧩 **Response Synthesis Node (`synthesize_response` / `synthesis_node.py`):** Assembles the final cohesive response for the API and UI.

---

## 🏁 Tech Stack

* **Language & Orchestration:** Python 3.12, LangGraph, LangChain, Pydantic
* **LLMs & Embeddings:** OpenAI (`gpt-4o`, `gpt-4o-mini`, `text-embedding-3-small`) and local Ollama (`qwen2.5:1.5b`) on desktop
* **Caching:** Redis semantic cache (`semcache*`) and prompt caching / modular prompt templates (`system_prompts.py`, `agent_prompts.py`)
* **Retrieval & Storage:** ChromaDB (Vector DB), `rank-bm25`, SQLite, and session state persistence (`data/sessions/`)
* **API, UI, & Market Data:** FastAPI, Streamlit, Plotly, pandas, `yfinance`
* **Protocol, Containers, & Testing:** Model Context Protocol (MCP), Docker, Docker Compose, `pytest` (`run_finnie_tests.py`)

---

## 🧭 Dashboard

1. **Order Execution (`src/ui/views/order_execution.py`):** Supports trade/order workflows paired with risk suitability checks and guardrails.
2. **Market Intelligence (`src/ui/views/market_intel.py`):** Provides spot and historical price lookups, technical indicators, formatted tables, and interactive charts.
3. **Portfolio Analytics (`src/ui/views/portfolio_analytics.py`):** Displays portfolio holdings breakdowns, allocation metrics, quantitative/DCF insights, and compliance context.
4. **Knowledge Base & RAG (`src/ui/views/rag_inspector.py`):** Inspects Hybrid RAG (ChromaDB + BM25) retrieval results, confidence tiers, source attribution, and latency metrics.
5. **Assistant Chat (`src/ui/views/assistant_chat.py`):** Delivers multi-agent conversational responses via FastAPI and LangGraph with execution timers, Redis semantic cache badges, and persistent session history.

---

## 🚀 Quick Start & Reset

```bash
docker compose up -d --build
docker compose restart app
docker compose exec redis redis-cli --scan --pattern "semcache*" | xargs -r docker compose exec -T redis redis-cli del
python tests/run_finnie_tests.py
```

---

## ⚠️ Disclaimer
This application is built for educational, research, and informational purposes only and does not constitute personalized financial, investment, tax, or legal advice. Always verify market data, valuation assumptions, and risk suitability independently before making financial decisions.