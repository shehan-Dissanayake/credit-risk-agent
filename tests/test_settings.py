import pytest

from credit_risk_agent.config import Settings, get_settings


def test_defaults_are_safe() -> None:
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.max_steps == 12
    assert settings.anthropic_api_key is None


def test_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CRA_MAX_STEPS", "5")
    get_settings.cache_clear()
    try:
        assert get_settings().max_steps == 5
    finally:
        get_settings.cache_clear()
