import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env if present
basedir = Path(__file__).resolve().parent.parent
load_dotenv(basedir / ".env")

class Config:
    """Base application configuration."""
    SECRET_KEY = os.getenv("SECRET_KEY", "meditrack-ai-default-dev-secret-key-2026")
    FLASK_ENV = os.getenv("FLASK_ENV", "development")
    FLASK_DEBUG = os.getenv("FLASK_DEBUG", "0") == "1"

    # SQLite Database with concurrency timeout
    raw_db_url = os.getenv("DATABASE_URL")
    if raw_db_url and raw_db_url.startswith("sqlite:///") and not os.path.isabs(raw_db_url[10:]):
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{basedir / raw_db_url[10:]}"
    elif raw_db_url:
        SQLALCHEMY_DATABASE_URI = raw_db_url
    else:
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{basedir / 'meditrack.db'}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "connect_args": {"timeout": 30},  # 30 second timeout on locks for SQLite
        "pool_pre_ping": True,
    }

    # CORS Allowed Origins
    cors_env = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000")
    CORS_ORIGINS = [origin.strip() for origin in cors_env.split(",") if origin.strip()]

    # ML Risk Thresholds
    RISK_THRESHOLD_LOW = float(os.getenv("RISK_THRESHOLD_LOW", "0.30"))
    RISK_THRESHOLD_HIGH = float(os.getenv("RISK_THRESHOLD_HIGH", "0.60"))

    # Model Artifact Path
    raw_model_path = os.getenv("MODEL_ARTIFACT_PATH")
    if raw_model_path:
        target = Path(raw_model_path)
        MODEL_ARTIFACT_PATH = str((basedir / target).resolve()) if not target.is_absolute() else str(target)
    else:
        MODEL_ARTIFACT_PATH = str(basedir / "app" / "ml" / "artifacts" / "attendance_model.joblib")

    # OpenRouter LLM Configuration
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
    OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o")


class TestingConfig(Config):
    """Configuration for automated test suite."""
    TESTING = True
    FLASK_DEBUG = False
    OPENROUTER_API_KEY = None  # Ensure test suite runs offline & deterministic
    # Using an isolated file-backed sqlite database for tests to support concurrent connections
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{basedir / 'test_meditrack.db'}"
    SQLALCHEMY_ENGINE_OPTIONS = {
        "connect_args": {"timeout": 20},
        "pool_pre_ping": True,
    }
