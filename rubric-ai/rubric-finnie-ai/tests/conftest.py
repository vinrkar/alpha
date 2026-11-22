# tests/conftest.py

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env", override=False)

if not os.getenv("OPENAI_API_KEY") and os.getenv("API_KEY"):
    os.environ["OPENAI_API_KEY"] = os.environ["API_KEY"]