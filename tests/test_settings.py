import pytest

from credit_risk_agent.config import Settings, get_settings


def test_defaults_are_safe() -> None:
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.max_steps == 12
    assert settings.embedding_model == "bge-m3"
    assert settings.embedding_dim == 1024
    assert settings.anthropic_api_key is None


def test_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CRA_MAX_STEPS", "5")
    monkeypatch.setenv("CRA_EMBEDDING_MODEL", "text-embedding-3-large")
    monkeypatch.setenv("CRA_EMBEDDING_DIM", "1536")
    get_settings.cache_clear()
    try:
        settings = get_settings()
        assert settings.max_steps == 5
        assert settings.embedding_model == "text-embedding-3-large"
        assert settings.embedding_dim == 1536
    finally:
        get_settings.cache_clear()
