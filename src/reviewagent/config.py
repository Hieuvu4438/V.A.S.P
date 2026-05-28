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


class RedisSettings(BaseModel):
    url: str = "redis://localhost:6379/0"
    cms_ttl_seconds: int = 86400


class ORCIDSettings(BaseModel):
    client_id: str = ""
    client_secret: str = ""
    token_url: str = "https://orcid.org/oauth/token"
    api_base_url: str = "https://pub.orcid.org/v3.0"


class CelerySettings(BaseModel):
    broker_url: str = "redis://localhost:6379/1"
    result_backend: str = "redis://localhost:6379/2"
    task_default_queue: str = "reviewagent"


class SnapshotSettings(BaseModel):
    mjl_path: str = "snapshots/mjl_current.csv"
    scimago_path: str = "snapshots/scimago_jcr.csv"
    beall_path: str = "snapshots/beall.csv"
    doaj_path: str = "snapshots/doaj.csv"


class AuditSettings(BaseModel):
    secret_key: str = ""


class ThresholdSettings(BaseModel):
    auto_approve: float = 0.90
    auto_reject: float = 0.65


class APIsSettings(BaseModel):
    crossref_base_url: str = "https://api.crossref.org"
    openalex_base_url: str = "https://api.openalex.org"


class LLMSettings(BaseModel):
    provider: str = "openrouter"
    api_key: str = ""
    model: str = "nvidia/nemotron-3-super-120b-a12b:free"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    timeout_seconds: int = 60
    self_consistency_k: int = 3
    cove_enabled: bool = True


class Settings(BaseSettings):
    app: AppSettings = Field(default_factory=AppSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    orcid: ORCIDSettings = Field(default_factory=ORCIDSettings)
    celery: CelerySettings = Field(default_factory=CelerySettings)
    snapshot: SnapshotSettings = Field(default_factory=SnapshotSettings)
    audit: AuditSettings = Field(default_factory=AuditSettings)
    threshold: ThresholdSettings = Field(default_factory=ThresholdSettings)
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
