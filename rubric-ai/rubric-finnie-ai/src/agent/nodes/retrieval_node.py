import logging
import os
import re
from typing import Any

import chromadb

from src.agent.state import FinancialAssistantState
from src.core.config import settings
from src.core.guardrails import truncate_text_by_words

logger = logging.getLogger(__name__)

_TICKER_MAP = {
    "apple": "AAPL",
    "aapl": "AAPL",
    "microsoft": "MSFT",
    "msft": "MSFT",
    "google": "GOOGL",
    "alphabet": "GOOGL",
    "googl": "GOOGL",
    "goog": "GOOGL",
    "amd": "AMD",
}


def _infer_query_ticker(query: str, fallback_ticker: str | None) -> str | None:
    q_lower = query.lower()
    for token, sym in _TICKER_MAP.items():
        if re.search(rf"\b{re.escape(token)}\b", q_lower):
            return sym
    upper_matches = re.findall(r"\b[A-Z]{2,5}\b", query)
    ignore = {"DCF", "RAG", "SEC", "RSI", "MACD", "FCF", "PV", "TV", "NPV", "IPO", "ETF", "USD"}
    for cand in upper_matches:
        if cand not in ignore:
            return cand
    return fallback_ticker.upper().strip() if fallback_ticker else None


def retrieval_node(state: FinancialAssistantState) -> dict[str, Any]:
    """Retrieves financial articles and SEC filing snippets from ChromaDB scoped to target ticker."""
    query = (state.get("user_query") or "").strip()
    logger.info("Executing retrieval_node for query: '%s'", query)

    if not query:
        logger.debug("Retrieval skipped: empty user query.")
        return {
            "retrieved_documents": [],
            "last_active_ticker": state.get("last_active_ticker"),
        }

    retrieved_docs: list[dict[str, Any]] = []
    target_ticker = _infer_query_ticker(query, state.get("last_active_ticker"))

    try:
        chroma_host = os.getenv("CHROMA_HOST", settings.CHROMA_HOST)
        chroma_port = int(os.getenv("CHROMA_PORT", str(settings.CHROMA_PORT)))
        collection_name = os.getenv("CHROMA_COLLECTION_NAME", settings.CHROMA_COLLECTION_NAME)

        client = chromadb.HttpClient(host=chroma_host, port=chroma_port)
        collection = client.get_collection(collection_name)

        query_kwargs: dict[str, Any] = {"query_texts": [query], "n_results": 5}
        if target_ticker:
            try:
                results = collection.query(
                    query_texts=[query],
                    n_results=3,
                    where={"ticker": target_ticker},
                )
            except Exception:
                results = collection.query(**query_kwargs)
        else:
            results = collection.query(**query_kwargs)

        documents_batch = results.get("documents") or []
        if documents_batch and documents_batch[0]:
            documents = documents_batch[0]
            metadatas_batch = results.get("metadatas") or []
            metadatas = (
                metadatas_batch[0]
                if metadatas_batch and metadatas_batch[0]
                else [{}] * len(documents)
            )
            distances_batch = results.get("distances") or []
            distances = distances_batch[0] if distances_batch and distances_batch[0] else []

            candidate_docs: list[dict[str, Any]] = []
            for idx, doc_text in enumerate(documents):
                if not doc_text:
                    continue
                meta = metadatas[idx] if idx < len(metadatas) and isinstance(metadatas[idx], dict) else {}
                dist = distances[idx] if idx < len(distances) and distances[idx] is not None else 0.1
                score = round(max(0.001, 1.0 / (1.0 + float(dist))), 4)
                doc_ticker = str(meta.get("ticker") or "").upper().strip()

                candidate_docs.append(
                    {
                        "content": truncate_text_by_words(str(doc_text), settings.MAX_INPUT_WORDS),
                        "metadata": meta,
                        "ticker": doc_ticker,
                        "score": score,
                        "source": meta.get("source", "sec_edgar_10q"),
                    }
                )

            if target_ticker:
                matched = [d for d in candidate_docs if d.get("ticker") == target_ticker]
                if matched:
                    retrieved_docs = matched[:3]
                else:
                    # Only keep docs that do not explicitly belong to a different ticker
                    unconflicted = [d for d in candidate_docs if not d.get("ticker")]
                    retrieved_docs = unconflicted[:3]
            else:
                retrieved_docs = candidate_docs[:3]

            if target_ticker:
                state_ticker = target_ticker
            elif retrieved_docs and retrieved_docs[0].get("ticker"):
                state_ticker = retrieved_docs[0]["ticker"]
            else:
                state_ticker = state.get("last_active_ticker")

            logger.info("Retrieved %d ticker-scoped documents from ChromaDB.", len(retrieved_docs))
        else:
            state_ticker = target_ticker or state.get("last_active_ticker")
            logger.warning("No matching documents found in collection '%s'.", collection_name)
    except Exception as exc:
        state_ticker = target_ticker or state.get("last_active_ticker")
        logger.error("ChromaDB retrieval failed: %s", exc)

    return {
        "retrieved_documents": retrieved_docs,
        "last_active_ticker": state_ticker,
        "current_step": "retrieval_completed",
    }