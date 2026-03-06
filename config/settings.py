"""Centralized configuration via pydantic-settings. All env vars flow through here."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # API keys (default empty -- agents fail gracefully on use)
    GOOGLE_API_KEY: str = ""
    POLYGON_API_KEY: str = ""
    FRED_API_KEY: str = ""
    NEWS_API_KEY: str = ""

    # Environment and infrastructure
    ENVIRONMENT: str = "local"
    SQLITE_DB_PATH: str = "data/equityiq.db"
    GCP_PROJECT_ID: str = ""
    GCP_REGION: str = "us-central1"
    LOG_LEVEL: str = "INFO"

    # Agent URLs (local defaults matching assigned ports)
    VALUATION_AGENT_URL: str = "http://localhost:8001"
    MOMENTUM_AGENT_URL: str = "http://localhost:8002"
    PULSE_AGENT_URL: str = "http://localhost:8003"
    ECONOMY_AGENT_URL: str = "http://localhost:8004"
    COMPLIANCE_AGENT_URL: str = "http://localhost:8005"
    SYNTHESIZER_AGENT_URL: str = "http://localhost:8006"
    RISK_AGENT_URL: str = "http://localhost:8007"

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached Settings singleton."""
    return Settings()
