# src/rag/bm25_retriever.py

import logging
from typing import Any, Mapping, Sequence

from rank_bm25 import BM25Okapi

logger = logging.getLogger(__name__)

class BM25Retriever:
    """Performs sparse keyword-based retrieval using Okapi BM25."""

    def __init__(
            self,
            corpus: Sequence[str],
            metadatas: Sequence[Mapping[str, Any]],
            ids: Sequence[str],
    ) -> None:
        self.corpus = list(corpus)
        self.metadatas = list(metadatas)
        self.ids = list(ids)
        self.tokenized_corpus = [doc.lower().split() for doc in self.corpus]
        self.bm25 = BM25Okapi(self.tokenized_corpus) if self.corpus else None
        logger.info("Initialized BM25Retriever with %d corpus documents.", len(self.corpus))

    def search(self, query: str, top_k: int = 4) -> list[dict[str, Any]]:
        """Retrieves top-k documents matching keyword frequencies."""
        if not self.corpus or not self.bm25:
            logger.warning("BM25 search attempted with empty corpus or uninitialized index.")
            return []

        tokenized_query = query.lower().split()
        scores = self.bm25.get_scores(tokenized_query)
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]

        results: list[dict[str, Any]] = []
        for idx in top_indices:
            if scores[idx] > 0:
                results.append(
                    {
                        "id": self.ids[idx],
                        "content": self.corpus[idx],
                        "metadata": self.metadatas[idx],
                        "score": float(scores[idx]),
                        "retrieval_type": "sparse_bm25",
                    }
                )
        logger.debug("BM25 search for '%s' returned %d results.", query, len(results))
        return results