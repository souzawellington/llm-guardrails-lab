import pytest
from app.settings import load_settings


def test_openai_key_is_a_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("LLM_BASE_URL", "https://example.test/v1")
    settings = load_settings()
    assert settings.llm_api_key == "test-key"
    assert settings.llm_base_url == "https://example.test/v1"
    assert settings.llm_host == "example.test"


def test_explicit_lab_key_wins(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_API_KEY", "lab-key")
    monkeypatch.setenv("OPENAI_API_KEY", "other-key")
    settings = load_settings()
    assert settings.llm_api_key == "lab-key"


def test_reasoning_budget(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_TIMEOUT_SECONDS", "300")
    monkeypatch.setenv("LLM_MAX_TOKENS", "256")
    monkeypatch.setenv("REASONING_EFFORT", "Low")
    settings = load_settings()
    assert settings.llm_timeout_seconds == 300
    assert settings.llm_max_tokens == 256
    assert settings.reasoning_effort == "low"
    assert settings.completion_fields() == {"max_tokens": 256, "reasoning_effort": "low"}

    monkeypatch.setenv("LLM_MAX_TOKENS", "none")
    monkeypatch.setenv("REASONING_EFFORT", "")
    settings = load_settings()
    assert settings.llm_max_tokens is None
    assert settings.completion_fields() == {}

    monkeypatch.setenv("REASONING_EFFORT", "turbo")
    with pytest.raises(ValueError):
        load_settings()


def test_flags_and_bad_urls(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENABLE_PRESIDIO", "yes")
    monkeypatch.setenv("ENABLE_JAILBREAK_HEURISTICS", "0")
    monkeypatch.setenv("LLM_BASE_URL", "https://api.openai.com/v1/")
    settings = load_settings()
    assert settings.enable_presidio is True
    assert settings.enable_jailbreak_heuristics is False
    assert settings.llm_base_url == "https://api.openai.com/v1"

    monkeypatch.setenv("LLM_BASE_URL", "file:///tmp/model")
    with pytest.raises(ValueError):
        load_settings()

    monkeypatch.setenv("LLM_BASE_URL", "https://user:secret@example.test/v1")
    with pytest.raises(ValueError):
        load_settings()
