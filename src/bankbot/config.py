"""Central config: paths, date, model name. Everything else reads from here."""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

DB_PATH = Path(os.getenv("BANK_DB", ROOT / "data" / "bank.db"))
POLICY_DIR = ROOT / "docs" / "policies"
CHROMA_DIR = Path(os.getenv("CHROMA_DIR", ROOT / ".chroma"))

# For reproducible results, "today" is fixed to this date (the data is generated around it too)
AS_OF_DATE = "2026-10-01"

LLM_MODEL = os.getenv("LLM_MODEL", "deepseek:deepseek-chat")
# With EMBEDDINGS=fake, use fake vectors that need no model download; for tests only
EMBEDDINGS = os.getenv("EMBEDDINGS", "default")
