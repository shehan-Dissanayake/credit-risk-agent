"""Central configuration. All values come from environment variables prefixed CRA_.

Budgets here are the hard limits from the design doc (section 5.2): the agent must
escalate with a partial report instead of exceeding any of them.
"""

from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="CRA_", extra="ignore")

    environment: str = "dev"
    log_level: str = "INFO"
    trace_dir: Path = Path("traces")
    embedding_model: str = "BAAI/bge-m3"
    embedding_dim: int = 1024

    # Agent budgets (hard limits)
    max_steps: int = 12
    max_tokens_per_case: int = 60_000
    case_timeout_seconds: int = 120
    cost_cap_usd: float = 1.0

    # Secrets (never logged, never committed)
    anthropic_api_key: SecretStr | None = None
    database_url: SecretStr | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
