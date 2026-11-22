# tests/core/test_config.py

from src.core.config import Settings, settings

def test_default_settings() -> None:
    """Validates default configuration settings and expected types/values."""
    assert settings.LLM_MODEL in ["DESKTOP", "CLOUD"]
    assert settings.CHAT_MODEL in {"qwen2.5:1.5b", "gpt-4o-mini"}
    assert settings.EMBEDDING_MODEL == "text-embedding-3-small"
    assert settings.MAX_INPUT_WORDS == 400
    assert settings.MAX_OUTPUT_TOKENS == 550
    assert settings.CHROMA_COLLECTION_NAME == "finnieai_db"

def test_derived_api_urls() -> None:
    """Validates that dependent API URLs format correctly from BASE_URL."""
    custom_settings = Settings(BASE_URL="http://test-server:9000")
    assert custom_settings.PROFILES_API_URL == "http://test-server:9000/api/v1/profiles"
    assert custom_settings.CHAT_API_URL == "http://test-server:9000/api/v1/chat"