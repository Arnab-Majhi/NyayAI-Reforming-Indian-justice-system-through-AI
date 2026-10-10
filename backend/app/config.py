import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
DATA = Path(os.getenv("DATA_DIR", str(ROOT / "data"))).resolve()
STORAGE = os.getenv("STORAGE_MODE", "sqlite")
ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")
DEMO = os.getenv("DEMO_LOGIN", "true").lower() == "true"
SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"