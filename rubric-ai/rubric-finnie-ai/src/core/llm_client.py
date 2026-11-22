import logging
from typing import Optional

from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from src.core.config import settings

logger = logging.getLogger(__name__)

def get_llm(model_name: Optional[str] = None, temperature: float = 0.0) -> ChatOpenAI:
    """Initializes a ChatOpenAI client for CLOUD (OpenAI) or DESKTOP (Ollama)."""
    target = (settings.LLM_MODEL or "").strip().upper()
    resolved_model = model_name or settings.CHAT_MODEL

    if target == "CLOUD":
        if not settings.API_KEY:
            raise ValueError("API_KEY environment variable is missing for CLOUD target.")
        logger.info("Initializing LLM client | Target: CLOUD | Provider: OpenAI | Model: %s", resolved_model)
        return ChatOpenAI(
            model=resolved_model,
            temperature=temperature,
            max_tokens=settings.MAX_OUTPUT_TOKENS,
            api_key=settings.API_KEY,
        )

    logger.info(
        "Initializing LLM client | Target: DESKTOP | Provider: Ollama | Model: %s | URL: %s",
        resolved_model,
        settings.MODEL_BASE_URL,
    )
    return ChatOpenAI(
        base_url=settings.MODEL_BASE_URL,
        model=resolved_model,
        temperature=temperature,
        max_tokens=settings.MAX_OUTPUT_TOKENS,
        request_timeout=90.0,
        api_key="ollama",
    )

def get_embedding(text: str) -> list[float]:
    """Generates a text embedding vector for CLOUD (OpenAI) or DESKTOP (Ollama)."""
    target = (settings.LLM_MODEL or "").strip().upper()

    try:
        if target == "CLOUD":
            if not settings.API_KEY:
                raise ValueError("API_KEY is missing for CLOUD embedding target.")
            resolved_embed_model = getattr(settings, "EMBEDDING_MODEL", "text-embedding-3-small")
            logger.info("Generating embedding | Target: CLOUD | Model: %s", resolved_embed_model)
            embeddings_model = OpenAIEmbeddings(
                model=resolved_embed_model,
                api_key=settings.API_KEY,
            )
        else:
            resolved_embed_model = getattr(settings, "EMBEDDING_MODEL", "nomic-embed-text")
            logger.info(
                "Generating embedding | Target: DESKTOP | Model: %s | URL: %s",
                resolved_embed_model,
                settings.MODEL_BASE_URL,
            )
            embeddings_model = OpenAIEmbeddings(
                base_url=settings.MODEL_BASE_URL,
                model=resolved_embed_model,
                api_key="ollama",
            )

        return embeddings_model.embed_query(text)
    except Exception as exc:
        logger.error("Failed to generate embedding: %s", exc)
        return []