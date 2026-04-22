from functools import lru_cache

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseModel):
    env: str = "development"
    name: str = "ReviewAgent PTIT"
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"


class DatabaseSettings(BaseModel):
    url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/reviewagent"


class APIsSettings(BaseModel):
    crossref_base_url: str = "https://api.crossref.org"
    openalex_base_url: str = "https://api.openalex.org"


class LLMSettings(BaseModel):
    provider: str = "anthropic"
    api_key: str = ""
    model: str = "claude-opus-4-7"
    timeout_seconds: int = 30


class Settings(BaseSettings):
    app: AppSettings = Field(default_factory=AppSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    apis: APIsSettings = Field(default_factory=APIsSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
