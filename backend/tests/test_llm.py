import httpx
import pytest

from src.llm import (
    ConfigurationError,
    LLMError,
    OllamaLLM,
    OpenAICompatibleLLM,
    build_llm,
)

KEY = "gsk_super_secret_key_123"


class Resp:
    def __init__(self, status=200, body=None):
        self.status_code = status
        self._body = body if body is not None else {}
        self.text = str(body)

    def json(self):
        if isinstance(self._body, Exception):
            raise self._body
        return self._body


def _llm():
    return OpenAICompatibleLLM("https://api.groq.com/openai/v1/", KEY, "some-model", 0.2, 30)


# ------------------------------------------------------------------ factory
def test_factory_ollama_default():
    llm = build_llm(provider="ollama", model="llama3.2:3b", ollama_base_url="http://x")
    assert isinstance(llm, OllamaLLM)


def test_factory_groq_uses_builtin_url():
    llm = build_llm(provider="groq", model="m", ollama_base_url="", api_key=KEY)
    assert isinstance(llm, OpenAICompatibleLLM)
    assert llm._base == "https://api.groq.com/openai/v1"


def test_factory_xai_uses_builtin_url():
    llm = build_llm(provider="XAI", model="m", ollama_base_url="", api_key=KEY)
    assert llm._base == "https://api.x.ai/v1"


@pytest.mark.parametrize(
    "kwargs, fragment",
    [
        ({"provider": "groq", "model": "m", "api_key": ""}, "LLM_API_KEY"),
        ({"provider": "groq", "model": "llama3.2:3b", "api_key": KEY}, "LLM_MODEL"),
        ({"provider": "openai_compatible", "model": "m", "api_key": KEY}, "LLM_BASE_URL"),
        ({"provider": "nope", "model": "m"}, "Unknown LLM_PROVIDER"),
    ],
)
def test_factory_rejects_bad_config(kwargs, fragment):
    with pytest.raises(ConfigurationError, match=fragment):
        build_llm(ollama_base_url="", **kwargs)


# ----------------------------------------------------------------- requests
def test_generate_sends_expected_request_and_returns_text(monkeypatch):
    seen = {}

    def fake_post(url, json, headers, timeout):
        seen.update(url=url, json=json, headers=headers, timeout=timeout)
        return Resp(200, {"choices": [{"message": {"content": "  hello  "}}]})

    monkeypatch.setattr(httpx, "post", fake_post)
    assert _llm().generate("SYS", "PROMPT") == "hello"
    assert seen["url"] == "https://api.groq.com/openai/v1/chat/completions"
    assert seen["headers"]["Authorization"] == f"Bearer {KEY}"
    assert seen["json"]["model"] == "some-model"
    assert seen["json"]["messages"][0] == {"role": "system", "content": "SYS"}
    assert seen["json"]["messages"][1] == {"role": "user", "content": "PROMPT"}


@pytest.mark.parametrize(
    "status, fragment",
    [(401, "API key"), (403, "API key"), (404, "LLM_MODEL"), (429, "rate limit"), (500, "HTTP 500")],
)
def test_http_errors_map_to_clear_messages_without_leaking_key(monkeypatch, status, fragment):
    monkeypatch.setattr(httpx, "post", lambda *a, **k: Resp(status, {"error": KEY}))
    with pytest.raises(LLMError, match=fragment) as exc:
        _llm().generate("s", "p")
    assert KEY not in str(exc.value)


@pytest.mark.parametrize(
    "body",
    [{}, {"choices": []}, {"choices": [{"message": {"content": "   "}}]}, ValueError("bad json")],
)
def test_malformed_or_empty_responses_raise(monkeypatch, body):
    monkeypatch.setattr(httpx, "post", lambda *a, **k: Resp(200, body))
    with pytest.raises(LLMError):
        _llm().generate("s", "p")


def test_network_failure_raises_without_leaking_key(monkeypatch):
    def boom(*a, **k):
        raise httpx.ConnectError(f"cannot connect with {KEY}")

    monkeypatch.setattr(httpx, "post", boom)
    with pytest.raises(LLMError) as exc:
        _llm().generate("s", "p")
    assert KEY not in str(exc.value)


def test_is_available(monkeypatch):
    monkeypatch.setattr(httpx, "get", lambda *a, **k: Resp(200, {}))
    assert _llm().is_available() is True
    monkeypatch.setattr(httpx, "get", lambda *a, **k: Resp(401, {}))
    assert _llm().is_available() is False

    def boom(*a, **k):
        raise httpx.ConnectError("down")

    monkeypatch.setattr(httpx, "get", boom)
    assert _llm().is_available() is False


# ------------------------------------------------------- startup integration
def test_bad_llm_config_degrades_health_instead_of_crashing(settings, monkeypatch):
    from dataclasses import replace

    from fastapi.testclient import TestClient

    import app as app_module

    bad = replace(settings, llm_provider="groq", llm_api_key="", llm_model="m")
    monkeypatch.setattr(app_module, "SentenceTransformerEmbedder", lambda name: _FakeEmb())
    with TestClient(app_module.create_app(bad)) as c:
        body = c.get("/health").json()
        assert body["status"] == "degraded"
        assert "LLM_API_KEY" in str(body["components"]["vector_store"]["error"])
        assert c.post("/chat", json={"question": "hi"}).status_code == 503


class _FakeEmb:
    from .conftest import FakeEmbedder as _F

    def __new__(cls):
        return cls._F()
