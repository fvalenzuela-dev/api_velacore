from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "api_velacore"
    app_version: str = "0.1.0"
    twelve_data_api_key: str | None = None

    model_config = SettingsConfigDict(
        env_prefix="VELACORE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
