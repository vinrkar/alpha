from typing import Optional
from cryptography.fernet import Fernet
from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # --- Universal LLM & AI Engine Configuration ---
    LLM_MODEL: str = Field(default="DESKTOP", description="Options: CLOUD or DESKTOP")
    CHAT_MODEL: str = Field(..., description="Active chat model name defined in .env")
    EMBEDDING_MODEL: str = Field(..., description="Active text embedding model name defined in .env")
    MODEL_BASE_URL: Optional[str] = Field(default=None, description="Active provider API endpoint base URL")
    API_KEY: str = Field(..., description="Active provider API key or token defined in .env")

    REPLICATE_API_TOKEN: Optional[str] = None
    MAX_INPUT_WORDS: int = 400
    MAX_OUTPUT_TOKENS: int = 550

    # Fernet Session Encryption
    SESSION_ENCRYPTION_KEY: str = Field(default_factory=lambda: Fernet.generate_key().decode())

    # --- ChromaDB Vector Store Configuration ---
    CHROMA_HOST: str = "chromadb"
    CHROMA_PORT: int = 8000
    CHROMA_COLLECTION_NAME: str = "finnieai_db"
    CHROMA_SERVER_AUTH_TOKEN: Optional[str] = None

    # --- Redis Configuration ---
    REDIS_URI: str = "redis://redis:6379"

    # --- FastAPI Gateway Configuration ---
    BASE_URL: str = "http://localhost:8080"

    @computed_field
    @property
    def PROFILES_API_URL(self) -> str:
        return f"{self.BASE_URL.rstrip('/')}/api/v1/profiles"

    @computed_field
    @property
    def CHAT_API_URL(self) -> str:
        return f"{self.BASE_URL.rstrip('/')}/api/v1/chat"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()