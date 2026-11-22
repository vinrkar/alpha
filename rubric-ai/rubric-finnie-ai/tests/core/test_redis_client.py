# tests/core/test_redis_client.py

import json
from unittest.mock import AsyncMock, patch

import pytest

from src.core.redis_client import cosine_similarity, get_semantic_cache

def test_cosine_similarity_identical_vectors() -> None:
    vec = [1.0, 2.0, 3.0]
    score = cosine_similarity(vec, vec)
    assert pytest.approx(score, 0.0001) == 1.0

def test_cosine_similarity_orthogonal_vectors() -> None:
    v1 = [1.0, 0.0]
    v2 = [0.0, 1.0]
    score = cosine_similarity(v1, v2)
    assert score == 0.0

@pytest.mark.asyncio
async def test_get_semantic_cache_hit() -> None:
    expected_response = {
        "final_response": "cached answer",
        "full_historical_closes": {"2026-11-18": 225.30},
    }
    mock_redis = AsyncMock()
    mock_redis.get.return_value = json.dumps(
        {
            "query": "test query",
            "embedding": [1.0, 0.0],
            "response": expected_response,
        }
    )

    with patch("src.core.redis_client.redis_client", mock_redis):
        result = await get_semantic_cache(
            query_embedding=[1.0, 0.0],
            scope_key="global",
            query_text="test query",
            threshold=0.90,
        )
        assert result == expected_response
