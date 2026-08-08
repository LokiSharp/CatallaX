"""Application settings loaded from environment variables / .env."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for CatallaX."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="CATALLAX_",
        extra="ignore",
    )

    database_url: str = (
        "postgresql+psycopg://catallax:catallax@localhost:15432/catallax_dev"
    )
    env: str = "development"

    # Market-data provider selection for instrument (and later price) sync.
    # longbridge = Longbridge primary + AKShare fallback (default)
    # longbridge-only = Longbridge only
    # akshare = AKShare only
    market_data_provider: str = "longbridge"

    longbridge_app_key: str = ""
    longbridge_app_secret: str = ""
    longbridge_access_token: str = ""


settings = Settings()
