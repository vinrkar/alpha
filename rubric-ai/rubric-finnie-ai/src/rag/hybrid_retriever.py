# src/rag/hybrid_retriever.py

import logging
from typing import Any, Mapping, Optional, Sequence

from src.rag.bm25_retriever import BM25Retriever
from src.rag.vector_store import FinancialVectorStore
from src.utils.rag_utils import RRF_K_CONSTANT, compute_rrf_score, get_confidence_percentage

logger = logging.getLogger(__name__)

class HybridRetriever:
    """Combines ChromaDB (dense) and BM25 (sparse) retrieval using Reciprocal Rank Fusion."""

    def __init__(
            self,
            vector_store: Optional[FinancialVectorStore],
            documents: Sequence[str],
            metadatas: Sequence[Mapping[str, Any]],
            ids: Sequence[str],
    ) -> None:
        self.vector_store = vector_store
        self.bm25_retriever = BM25Retriever(corpus=documents, metadatas=metadatas, ids=ids)
        logger.info("HybridRetriever initialized successfully.")

    @staticmethod
    def _collect_ranks(
            results: Sequence[dict[str, Any]],
            doc_ranks: dict[str, list[int]],
            doc_store: dict[str, dict[str, Any]],
    ) -> None:
        for rank, doc in enumerate(results, start=1):
            doc_id = doc["id"]
            doc_store[doc_id] = doc
            doc_ranks.setdefault(doc_id, []).append(rank)

    def search(
            self,
            query: str,
            top_k: int = 4,
            rrf_k: int = RRF_K_CONSTANT,
    ) -> list[dict[str, Any]]:
        """Executes hybrid search and fuses rankings via Reciprocal Rank Fusion."""
        logger.info("Executing hybrid search for query: '%s' (top_k=%d)", query, top_k)
        dense_results = (
            self.vector_store.similarity_search(query, top_k=top_k * 2)
            if self.vector_store is not None
            else []
        )
        sparse_results = self.bm25_retriever.search(query, top_k=top_k * 2)

        doc_ranks: dict[str, list[int]] = {}
        doc_store: dict[str, dict[str, Any]] = {}
        self._collect_ranks(dense_results, doc_ranks, doc_store)
        self._collect_ranks(sparse_results, doc_ranks, doc_store)

        scored_docs: list[dict[str, Any]] = []
        for doc_id, ranks in doc_ranks.items():
            raw_score = compute_rrf_score(ranks, k=rrf_k)
            scored_docs.append(
                {
                    **doc_store[doc_id],
                    "rrf_score": round(raw_score, 4),
                    "confidence_percentage": get_confidence_percentage(raw_score),
                }
            )

        sorted_docs = sorted(scored_docs, key=lambda item: item["rrf_score"], reverse=True)
        logger.debug(
            "Hybrid search fused %d candidate documents down to top_k=%d.",
            len(sorted_docs),
            top_k,
        )
        return sorted_docs[:top_k]