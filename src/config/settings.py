"""Application settings via Pydantic Settings.

Loads configuration from environment variables and .env file.
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application configuration.

    Environment variables override defaults.
    Reads from .env file if present.
    """

    nango_webhook_secret: str = ""
    """HMAC secret for Nango webhook signature verification (required)"""

    nango_secret_key: str = ""
    """Nango Secret Key for API authentication (required for fetching records)"""

    nango_base_url: str = "https://api.nango.dev"
    """Nango API base URL"""

    database_url: str = "sqlite+aiosqlite:///./data.db"
    """Database connection string"""

    env: str = "production"
    """Environment: development, staging, production"""

    version: str = "1.0.0"
    """Application version for health check"""

    log_level: str = "INFO"
    """Logging level: DEBUG, INFO, WARNING, ERROR"""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
