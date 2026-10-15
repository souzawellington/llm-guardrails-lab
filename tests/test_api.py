import asyncio

import httpx
import pytest
from app.llm_client import LLMError, complete_chat
from app.main import app, reset_rails
from app.rails_runtime import GuardResult
from app.settings import Settings
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    reset_rails()
    with TestClient(app) as test_client:
        yield test_client
    reset_rails()


def test_health_and_chat_page(client: TestClient) -> None:
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    page = client.get("/ui")
    assert page.status_code == 200
    assert "Send" in page.text
    assert "LLM_API_KEY" not in page.text


def test_meta_hides_the_key(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_API_KEY", "super-secret")
    monkeypatch.setenv("LLM_BASE_URL", "https://models.example/v1")
    payload = client.get("/meta").json()
    assert payload["key_configured"] is True
    assert payload["llm_host"] == "models.example"
    assert "super-secret" not in str(payload)


def test_raw_chat_requires_a_key(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    response = client.post("/v1/chat/raw", json={"message": "hello"})
    assert response.status_code == 503


def test_raw_chat_returns_the_model_text(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LLM_API_KEY", "present")

    async def fake_complete(settings, message, client=None):
        del settings, client
        assert message == "What is a guardrail?"
        return "A check that runs on each message."

    monkeypatch.setattr("app.main.complete_chat", fake_complete)
    response = client.post("/v1/chat/raw", json={"message": "  What is a guardrail?  "})
    assert response.status_code == 200
    body = response.json()
    assert body["reply"] == "A check that runs on each message."
    assert body["guardrails"] == "off"
    assert body["blocked"] is False


def test_raw_chat_maps_model_errors(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_API_KEY", "present")

    async def fake_complete(settings, message, client=None):
        del settings, message, client
        raise LLMError("Model endpoint returned HTTP 429: slow down")

    monkeypatch.setattr("app.main.complete_chat", fake_complete)
    response = client.post("/v1/chat/raw", json={"message": "hello"})
    assert response.status_code == 502


def test_complete_chat_reads_an_openai_reply() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/chat/completions"
        assert request.headers["authorization"] == "Bearer lab-key"
        body = {"choices": [{"message": {"content": "hello back"}}]}
        return httpx.Response(200, json=body)

    settings = Settings(
        llm_api_key="lab-key",
        llm_base_url="https://example.test/v1",
        llm_model="demo",
    )
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    text = asyncio.run(complete_chat(settings, "hi", client=client))
    assert text == "hello back"


def test_blank_message_is_rejected(client: TestClient) -> None:
    response = client.post("/v1/chat/raw", json={"message": "   "})
    assert response.status_code == 422


def test_guarded_chat_uses_the_rails(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_API_KEY", "present")

    async def fake_guarded(rails, message):
        del rails
        assert message == "hello"
        return GuardResult(reply="Hello from the rails.", blocked=False)

    monkeypatch.setattr("app.main.guarded_reply", fake_guarded)
    monkeypatch.setattr("app.main.build_rails", lambda settings: object())
    response = client.post("/v1/chat/guarded", json={"message": "hello"})
    assert response.status_code == 200
    assert response.json()["guardrails"] == "on"
    assert response.json()["blocked"] is False
