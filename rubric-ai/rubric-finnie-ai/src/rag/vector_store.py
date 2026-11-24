# src/rag/vector_store.py

import logging
import os
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(dotenv_path=REPO_ROOT / ".env", override=False)
logger = logging.getLogger(__name__)


def _resolve_chromadb_endpoint(
        host: Optional[str],
        port: Optional[int],
        collection_name: Optional[str],
) -> tuple[str, int, str, Optional[str]]:
    is_docker = os.path.exists("/.dockerenv")
    default_host = "chromadb" if is_docker else "localhost"

    env_host = os.getenv("CHROMA_HOST")
    resolved_host = (
            host
            or (default_host if is_docker and env_host == "localhost" else env_host)
            or default_host
    )
    resolved_port = port or int(os.getenv("CHROMA_PORT", "8000"))
    resolved_collection = collection_name or os.getenv("CHROMA_COLLECTION_NAME", "finnieai_db")
    auth_token = os.getenv("CHROMA_SERVER_AUTH_TOKEN")
    return resolved_host, resolved_port, resolved_collection, auth_token


def _build_embedding_function() -> Any:
    provider = (os.getenv("CHROMA_EMBEDDING_PROVIDER") or "").strip().lower()
    if not provider or provider == "default":
        return embedding_functions.DefaultEmbeddingFunction()

    if provider == "openai":
        openai_key = os.getenv("API_KEY") or os.getenv("OPENAI_API_KEY")
        if not openai_key or openai_key.startswith("<"):
            raise ValueError(
                "CHROMA_EMBEDDING_PROVIDER='openai' requires a valid API_KEY or OPENAI_API_KEY."
            )
        return embedding_functions.OpenAIEmbeddingFunction(
            api_key=openai_key,
            model_name=os.getenv("EMBEDDING_MODEL", "text-embedding-3-large"),
        )

    raise ValueError(f"Unsupported CHROMA_EMBEDDING_PROVIDER: '{provider}'")


class FinancialVectorStore:
    """Manages persistent vector storage using ChromaDB."""

    def __init__(
            self,
            host: Optional[str] = None,
            port: Optional[int] = None,
            collection_name: Optional[str] = None,
    ) -> None:
        resolved_host, resolved_port, resolved_collection, auth_token = _resolve_chromadb_endpoint(
            host=host,
            port=port,
            collection_name=collection_name,
        )

        self.client: Any = None
        self.collection: Any = None

        try:
            client_headers = {"X-Chroma-Token": auth_token} if auth_token else None
            self.client = chromadb.HttpClient(
                host=resolved_host,
                port=resolved_port,
                headers=client_headers,
                settings=Settings(anonymized_telemetry=False),
            )

            embedding_fn = _build_embedding_function()
            self.collection = self.client.get_or_create_collection(
                name=resolved_collection,
                embedding_function=embedding_fn,
            )
        except Exception as exc:
            logger.error("ChromaDB connection failed: %s", exc)
            self.client = None
            self.collection = None

    def add_documents(
            self,
            documents: Sequence[str],
            metadatas: Sequence[Mapping[str, Any]],
            ids: Sequence[str],
    ) -> None:
        """Upserts financial articles or filing snippets into the vector collection."""
        if not self.collection:
            return
        self.collection.upsert(
            documents=list(documents),
            metadatas=[dict(m) for m in metadatas],
            ids=list(ids),
        )

    def similarity_search(self, query: str, top_k: int = 4) -> list[dict[str, Any]]:
        """Performs dense semantic vector search with graceful fallback."""
        if not self.collection:
            return []

        try:
            results = self.collection.query(query_texts=[query], n_results=top_k)
            docs_list = (results.get("documents") or [[]])[0]
            metas_list = (results.get("metadatas") or [[]])[0]
            ids_list = (results.get("ids") or [[]])[0]

            return [
                {
                    "id": doc_id,
                    "content": doc_text,
                    "metadata": meta,
                    "retrieval_type": "dense_vector",
                }
                for doc_text, meta, doc_id in zip(docs_list, metas_list, ids_list)
            ]
        except Exception as exc:
            logger.error("Vector search failed: %s", exc)
            return []