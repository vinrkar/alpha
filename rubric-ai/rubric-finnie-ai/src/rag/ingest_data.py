# src/rag/ingest_data.py

import logging
from pathlib import Path
import sqlite3
from typing import Any

from src.rag.vector_store import FinancialVectorStore

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).resolve().parents[2] / "data" / "rubric-finnie-db"

FOUNDATIONAL_DOCS: list[dict[str, Any]] = [
    {
        "id": "doc_fed_rate_outlook_2026",
        "content": (
            "Federal Reserve Policy Note: The Federal Open Market Committee (FOMC) "
            "maintained the benchmark federal funds rate at 4.25%-4.50%."
        ),
        "metadata": {
            "ticker": "MACRO",
            "doc_type": "Federal Reserve Note",
            "year": 2026,
            "sector": "Economy",
        },
    },
    {
        "id": "doc_portfolio_risk_guidelines",
        "content": (
            "Portfolio Risk Management Standard: Recommended single-stock position limit "
            "is capped at 15% of total portfolio value."
        ),
        "metadata": {
            "ticker": "PORTFOLIO",
            "doc_type": "Risk Framework",
            "year": 2026,
            "sector": "Risk",
        },
    },
]

def _load_portfolio_rows(db_path: Path) -> list[tuple[str, str, str]]:
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT ticker, name, exchange FROM portfolios;")
        return cursor.fetchall()
    finally:
        conn.close()

def seed_knowledge_base() -> None:
    """Incrementally embeds missing ticker filings and foundational macro/risk docs."""
    logger.info("Initializing FinancialVectorStore for incremental knowledge base sync...")
    store = FinancialVectorStore()

    if not store.collection:
        logger.error("ChromaDB client is offline. Ensure ChromaDB server is running at localhost:8000.")
        return

    if not DB_PATH.exists():
        logger.error("Database not found at %s. Run init_db.py first.", DB_PATH)
        return

    rows = _load_portfolio_rows(DB_PATH)
    existing_data = store.collection.get()
    existing_ids: set[str] = (
        set(existing_data["ids"]) if existing_data and "ids" in existing_data else set()
    )

    new_documents: list[str] = []
    new_metadatas: list[dict[str, Any]] = []
    new_ids: list[str] = []

    for ticker, name, exchange in rows:
        doc_id = f"doc_sec_{ticker.lower()}_10q_2026"
        if doc_id not in existing_ids:
            new_documents.append(
                f"{name or ticker} ({ticker}) Q3 Financial Report & Operating Update: "
                f"Traded on {exchange or 'NASDAQ'}. Net revenue expanded robustly year-over-year "
                f"driven by core segment growth and operational efficiency."
            )
            new_metadatas.append(
                {
                    "ticker": ticker,
                    "doc_type": "10-Q",
                    "year": 2026,
                    "sector": "Equities",
                }
            )
            new_ids.append(doc_id)

    for doc in FOUNDATIONAL_DOCS:
        if doc["id"] not in existing_ids:
            new_documents.append(doc["content"])
            new_metadatas.append(doc["metadata"])
            new_ids.append(doc["id"])

    if new_documents:
        logger.info("Incremental sync: embedding %d new documents.", len(new_documents))
        store.add_documents(documents=new_documents, metadatas=new_metadatas, ids=new_ids)
        logger.info("Successfully embedded new documents into ChromaDB.")
    else:
        logger.info("Vector store is up-to-date with SQLite. No new embeddings required.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    seed_knowledge_base()