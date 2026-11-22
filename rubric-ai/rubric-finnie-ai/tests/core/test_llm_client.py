# tests/core/test_llm_client.py

from unittest.mock import MagicMock, patch
import pytest

from src.core.config import settings
from src.core.llm_client import get_embedding, get_llm

def test_get_llm_desktop_target(monkeypatch: pytest.MonkeyPatch) -> None:
    """Validates that DESKTOP target initializes Ollama client configuration."""
    monkeypatch.setattr(settings, "LLM_MODEL", "DESKTOP")
    with patch("src.core.llm_client.ChatOpenAI") as mock_chat:
        get_llm()
        mock_chat.assert_called_once()
        _, kwargs = mock_chat.call_args
        assert kwargs["base_url"] == settings.MODEL_BASE_URL
        assert kwargs["api_key"] == "ollama"

def test_get_llm_cloud_missing_key_raises_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Validates that CLOUD target raises ValueError if API_KEY is missing."""
    monkeypatch.setattr(settings, "LLM_MODEL", "CLOUD")
    monkeypatch.setattr(settings, "API_KEY", None)

    with pytest.raises(ValueError, match="API_KEY environment variable is missing"):
        get_llm()

def test_get_embedding_fallback_on_error() -> None:
    """Validates safe empty list fallback if embedding generation fails."""
    with patch("src.core.llm_client.OpenAIEmbeddings") as mock_embeddings:
        mock_instance = MagicMock()
        mock_instance.embed_query.side_effect = Exception("API Error")
        mock_embeddings.return_value = mock_instance

        result = get_embedding("test query")
        assert result == []