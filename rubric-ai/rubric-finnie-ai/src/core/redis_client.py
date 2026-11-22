import hashlib
import json
import logging
import time
from typing import Any, Optional

from langgraph.checkpoint.memory import MemorySaver
import numpy as np

from src.core.config import settings

logger = logging.getLogger(__name__)

REDIS_URI = settings.REDIS_URI
MAX_CACHE_ENTRIES_PER_SCOPE = 50

try:
    from langgraph.checkpoint.redis.aio import AsyncRedisSaver

    checkpointer = AsyncRedisSaver(redis_url=REDIS_URI)
    logger.info("Initialized AsyncRedisSaver connected to %s", REDIS_URI)
except Exception as exc:
    logger.warning("AsyncRedisSaver unavailable (%s); falling back to MemorySaver.", exc)
    checkpointer = MemorySaver()

redis_client = None
try:
    import redis.asyncio as aioredis

    redis_client = aioredis.from_url(REDIS_URI, decode_responses=True)
    logger.info("Initialized Redis async client for caching.")
except Exception as exc:
    logger.warning("Redis async client unavailable for caching: %s", exc)


def _build_cache_key(
        scope_key: str,
        query_text: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
) -> str:
    date_modifier = f":{start_date}:{end_date}" if start_date and end_date else ""
    identifier = f"{query_text.strip().lower()}{date_modifier}"
    query_hash = hashlib.md5(identifier.encode("utf-8")).hexdigest()
    return f"semcache:{scope_key}:{query_hash}"


def cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    """Computes cosine similarity between two embedding vectors."""
    v1 = np.array(vec1, dtype=float)
    v2 = np.array(vec2, dtype=float)
    norm1 = float(np.linalg.norm(v1))
    norm2 = float(np.linalg.norm(v2))
    if norm1 == 0.0 or norm2 == 0.0:
        return 0.0
    return float(np.dot(v1, v2) / (norm1 * norm2))


async def get_semantic_cache(
        query_embedding: list[float],
        scope_key: str,
        query_text: str,
        threshold: float = 0.85,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        require_closes: bool = False,
) -> Optional[dict[str, Any]]:
    """Retrieves cached response using deterministic query-string and date-bound hashing."""
    if not redis_client or not query_text:
        return None

    try:
        exact_key = _build_cache_key(scope_key, query_text, start_date, end_date)
        cached_data_str = await redis_client.get(exact_key)
        if not cached_data_str:
            logger.debug("Cache miss for key %s", exact_key)
            return None

        cache_entry = json.loads(cached_data_str)
        response_payload = cache_entry.get("response", {})
        closes = response_payload.get("full_historical_closes", {})
        final_resp = str(response_payload.get("final_response", "") or "").strip()

        has_valid_text = bool(final_resp) and "No data available" not in final_resp
        has_valid_closes = isinstance(closes, dict) and len(closes) > 0

        if (not require_closes and has_valid_text) or (require_closes and has_valid_closes and has_valid_text):
            logger.info("Cache hit for scope=%s query=%r", scope_key, query_text)
            return response_payload

        logger.warning("Purging empty or poisoned cache entry: %s", exact_key)
        await redis_client.delete(exact_key)
        return None
    except Exception as exc:
        logger.error("Error during cache lookup: %s", exc)
        return None


async def set_semantic_cache(
        query_embedding: list[float],
        scope_key: str,
        query_text: str,
        response_data: dict[str, Any],
        ttl: int = 3600,
        max_entries: int = MAX_CACHE_ENTRIES_PER_SCOPE,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
) -> None:
    """Stores a response entry in Redis and maintains bounded LRU entries per scope."""
    if not redis_client or not query_embedding:
        return

    try:
        cache_key = _build_cache_key(scope_key, query_text, start_date, end_date)
        lru_index_key = f"semcache_lru:{scope_key}"

        cache_payload = {
            "query": query_text,
            "embedding": query_embedding,
            "response": response_data,
            "start_date": start_date,
            "end_date": end_date,
        }
        await redis_client.set(cache_key, json.dumps(cache_payload), ex=ttl)
        await redis_client.zadd(lru_index_key, {cache_key: time.time()})
        await redis_client.expire(lru_index_key, ttl)

        current_count = await redis_client.zcard(lru_index_key)
        if current_count > max_entries:
            overflow = current_count - max_entries
            oldest_keys = await redis_client.zrange(lru_index_key, 0, overflow - 1)
            if oldest_keys:
                await redis_client.delete(*oldest_keys)
                await redis_client.zrem(lru_index_key, *oldest_keys)
                logger.info("Evicted %d LRU cache entries for scope %s", len(oldest_keys), scope_key)
    except Exception as exc:
        logger.error("Error during cache write: %s", exc)