import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from backend/ directory automatically
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path, override=True)


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-in-production")
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "mysql+pymysql://root:root@127.0.0.1:3306/contractguard",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JSON_SORT_KEYS = False

    # Session cookie must be sent with cross-port requests (frontend:5173 -> backend:5000)
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = False   # True only in production (HTTPS)
    SESSION_COOKIE_HTTPONLY = True

    # Admin account bootstrap (change in production via backend/.env).
    ADMIN_NAME = os.getenv("ADMIN_NAME", "System Admin")
    ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@contractguard.local")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "Admin@123456")

    # LLM risk explanation (DashScope Qwen API)
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "dashscope")
    LLM_MODEL = os.getenv("LLM_MODEL", "qwen3.5-flash")
    LLM_API_KEY = os.getenv("DASHSCOPE_API_KEY", os.getenv("LLM_API_KEY", ""))
    LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    LLM_ENABLED = os.getenv("LLM_ENABLED", "true").lower() == "true"
    LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "30"))
    LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "300"))
    LLM_MAX_CONCURRENCY = int(os.getenv("LLM_MAX_CONCURRENCY", "3"))
    LLM_CONTRACT_TIMEOUT = int(os.getenv("LLM_CONTRACT_TIMEOUT", "150"))
    LLM_RETRY_COUNT = int(os.getenv("LLM_RETRY_COUNT", "1"))
    LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.3"))
