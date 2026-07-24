import httpx
import openai
import pytest

from app.core.config import Settings
from app.services import llm_client

pytestmark = pytest.mark.anyio

_SECRET_MARKER = "SECRET-MARKER-do-not-leak"


def _settings(**overrides) -> Settings:
    return Settings(_env_file=None, **overrides)


def test_is_configured_true_for_official_openai_endpoint(monkeypatch):
    monkeypatch.setattr(
        llm_client,
        "get_settings",
        lambda: _settings(llm_provider="openai", llm_model="gpt-4o-mini", llm_api_key="key"),
    )
    assert llm_client.is_configured() is True


def test_is_configured_false_when_provider_not_openai_without_base_url(monkeypatch):
    monkeypatch.setattr(
        llm_client,
        "get_settings",
        lambda: _settings(llm_provider="gemini", llm_model="m", llm_api_key="key"),
    )
    assert llm_client.is_configured() is False


def test_is_configured_true_with_base_url_and_nonblank_provider(monkeypatch):
    monkeypatch.setattr(
        llm_client,
        "get_settings",
        lambda: _settings(
            llm_provider="gemini", llm_model="m", llm_api_key="key", llm_base_url="https://example/v1"
        ),
    )
    assert llm_client.is_configured() is True


def test_is_configured_false_when_provider_blank_with_base_url(monkeypatch):
    monkeypatch.setattr(
        llm_client,
        "get_settings",
        lambda: _settings(
            llm_provider="  ", llm_model="m", llm_api_key="key", llm_base_url="https://example/v1"
        ),
    )
    assert llm_client.is_configured() is False


@pytest.mark.parametrize("field", ["llm_model", "llm_api_key"])
def test_is_configured_false_when_required_field_blank(monkeypatch, field):
    kwargs = {"llm_provider": "openai", "llm_model": "m", "llm_api_key": "key"}
    kwargs[field] = "   "
    monkeypatch.setattr(llm_client, "get_settings", lambda: _settings(**kwargs))
    assert llm_client.is_configured() is False


def test_is_configured_false_when_nothing_set(monkeypatch):
    monkeypatch.setattr(llm_client, "get_settings", lambda: _settings())
    assert llm_client.is_configured() is False


async def test_complete_json_raises_llm_unavailable_when_not_configured(monkeypatch):
    monkeypatch.setattr(llm_client, "get_settings", lambda: _settings())
    client = llm_client.OpenAICompatibleLLMClient()
    with pytest.raises(llm_client.LLMUnavailableError) as excinfo:
        await client.complete_json("sys", "user", max_completion_tokens=100)
    assert excinfo.value.reason == "configuration_error"


def test_llm_unavailable_error_defaults_to_provider_error_reason():
    exc = llm_client.LLMUnavailableError("boom")
    assert exc.reason == "provider_error"


async def test_aclose_is_noop_when_client_never_created():
    client = llm_client.OpenAICompatibleLLMClient()
    await client.aclose()  # 예외 없이 조용히 반환되어야 한다.


async def test_complete_json_translates_sdk_error_without_leaking_message(monkeypatch):
    monkeypatch.setattr(
        llm_client,
        "get_settings",
        lambda: _settings(llm_provider="openai", llm_model="m", llm_api_key="key"),
    )

    client = llm_client.OpenAICompatibleLLMClient()

    class _FakeCompletions:
        async def create(self, **kwargs):
            raise openai.APIConnectionError(
                message=f"boom {_SECRET_MARKER}", request=_DummyRequest()
            )

    await _install_fake_sdk_client(client, _FakeCompletions())

    with pytest.raises(llm_client.LLMUnavailableError) as excinfo:
        await client.complete_json("sys", "user", max_completion_tokens=100)

    assert _SECRET_MARKER not in str(excinfo.value)
    assert excinfo.value.reason == "provider_error"


async def test_complete_json_translates_rate_limit_error_without_leaking_message(monkeypatch):
    monkeypatch.setattr(
        llm_client,
        "get_settings",
        lambda: _settings(llm_provider="openai", llm_model="m", llm_api_key="key"),
    )

    client = llm_client.OpenAICompatibleLLMClient()

    class _RateLimitedCompletions:
        async def create(self, **kwargs):
            raise openai.RateLimitError(
                f"quota exceeded {_SECRET_MARKER}", response=_fake_httpx_response(429), body=None
            )

    await _install_fake_sdk_client(client, _RateLimitedCompletions())

    with pytest.raises(llm_client.LLMUnavailableError) as excinfo:
        await client.complete_json("sys", "user", max_completion_tokens=100)

    assert excinfo.value.reason == "rate_limited"
    assert _SECRET_MARKER not in str(excinfo.value)


async def test_complete_json_translates_empty_response_with_empty_response_reason(monkeypatch):
    monkeypatch.setattr(
        llm_client,
        "get_settings",
        lambda: _settings(llm_provider="openai", llm_model="m", llm_api_key="key"),
    )

    client = llm_client.OpenAICompatibleLLMClient()

    class _EmptyMessage:
        content = None

    class _EmptyChoice:
        message = _EmptyMessage()

    class _EmptyResponse:
        choices = [_EmptyChoice()]

    class _EmptyCompletions:
        async def create(self, **kwargs):
            return _EmptyResponse()

    await _install_fake_sdk_client(client, _EmptyCompletions())

    with pytest.raises(llm_client.LLMUnavailableError) as excinfo:
        await client.complete_json("sys", "user", max_completion_tokens=100)

    assert excinfo.value.reason == "empty_response"


async def test_complete_text_translates_timeout_without_leaking_message(monkeypatch):
    monkeypatch.setattr(
        llm_client,
        "get_settings",
        lambda: _settings(llm_provider="openai", llm_model="m", llm_api_key="key"),
    )
    monkeypatch.setattr(llm_client, "LLM_CALL_TIMEOUT_SECONDS", 0.01)

    client = llm_client.OpenAICompatibleLLMClient()

    class _SlowCompletions:
        async def create(self, **kwargs):
            import asyncio

            await asyncio.sleep(1)
            raise AssertionError("should have timed out before reaching here")

    await _install_fake_sdk_client(client, _SlowCompletions())

    with pytest.raises(llm_client.LLMUnavailableError) as excinfo:
        await client.complete_text("sys", "user", max_completion_tokens=100)

    assert "timed out" in str(excinfo.value).lower()
    assert excinfo.value.reason == "timeout"


async def test_reuses_internal_client_across_calls(monkeypatch):
    monkeypatch.setattr(
        llm_client,
        "get_settings",
        lambda: _settings(llm_provider="openai", llm_model="m", llm_api_key="key"),
    )
    client = llm_client.OpenAICompatibleLLMClient()

    first, _ = await client._ensure_client()
    second, _ = await client._ensure_client()
    assert first is second


class _DummyRequest:
    def __init__(self) -> None:
        self.method = "POST"
        self.url = "https://example.test/v1/chat/completions"


def _fake_httpx_response(status_code: int) -> httpx.Response:
    request = httpx.Request("POST", "https://example.test/v1/chat/completions")
    return httpx.Response(status_code=status_code, request=request)


class _FakeChat:
    def __init__(self, completions) -> None:
        self.completions = completions


async def _install_fake_sdk_client(client: "llm_client.OpenAICompatibleLLMClient", completions) -> None:
    real_client, model = await client._ensure_client()
    real_client.chat = _FakeChat(completions)
