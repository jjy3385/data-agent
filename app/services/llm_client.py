"""단일 LLM Provider와의 비동기 통신 경계.

OpenAI Chat Completions 호환 API(`AsyncOpenAI`)만 사용한다. LLM_PROVIDER는 SDK 선택을
분기하지 않는 식별용 설정값이다. Wrapper 생성 자체는 검증·네트워크 호출을 하지 않으며,
첫 호출에서 설정을 검증하고 내부 AsyncOpenAI Instance를 지연 생성해 재사용한다.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, Protocol

from openai import AsyncOpenAI, OpenAIError, RateLimitError

from app.core.config import get_settings

LLM_CALL_TIMEOUT_SECONDS = 20.0
LLM_MAX_RETRIES = 1


class LLMUnavailableError(RuntimeError):
    """LLM 설정이 없거나 유효하지 않거나 Provider 호출에 실패했을 때 발생한다.

    공개 Contract의 code(`llm_unavailable`)는 이 예외 하나로만 매핑되며 바뀌지 않는다.
    `reason`은 Backend 내부에서만 쓰는 세분화 값이며 API 응답에는 노출하지 않는다:
    "configuration_error"(설정 누락·무효), "timeout"(전체 호출 Timeout),
    "rate_limited"(Provider Rate Limit), "provider_error"(그 외 Provider 오류),
    "empty_response"(빈 응답). 알려지지 않은 값이 들어와도 호출부가 깨지지 않도록
    기본값을 "provider_error"로 둔다.
    """

    def __init__(self, message: str, *, reason: str = "provider_error") -> None:
        super().__init__(message)
        self.reason = reason


class LLMClient(Protocol):
    async def complete_json(
        self, system_prompt: str, user_prompt: str, max_completion_tokens: int
    ) -> dict[str, Any]: ...

    async def complete_text(
        self, system_prompt: str, user_prompt: str, max_completion_tokens: int
    ) -> str: ...


def _validate_settings() -> tuple[str, str, str | None]:
    """(api_key, model, base_url)를 반환하거나 LLMUnavailableError를 던진다."""
    settings = get_settings()
    provider = (settings.llm_provider or "").strip()
    model = (settings.llm_model or "").strip()
    api_key = (settings.llm_api_key or "").strip()
    base_url = (settings.llm_base_url or "").strip() or None

    if not model or not api_key:
        raise LLMUnavailableError(
            "LLM_MODEL and LLM_API_KEY must be configured", reason="configuration_error"
        )

    if base_url is None:
        if provider != "openai":
            raise LLMUnavailableError(
                'LLM_PROVIDER must be exactly "openai" when LLM_BASE_URL is not set',
                reason="configuration_error",
            )
    else:
        if not provider:
            raise LLMUnavailableError(
                "LLM_PROVIDER must not be blank when LLM_BASE_URL is set", reason="configuration_error"
            )

    return api_key, model, base_url


def is_configured() -> bool:
    """OpenAICompatibleLLMClient와 동일한 규칙으로 현재 설정이 유효한지만 확인한다.

    API Key 값 자체는 반환하지 않는다. requires_llm pytest 자동 Skip 판단에 사용한다.
    """
    try:
        _validate_settings()
    except LLMUnavailableError:
        return False
    return True


class OpenAICompatibleLLMClient:
    """Wrapper 생성은 항상 성공한다(Startup을 막지 않음). 내부 AsyncOpenAI는 첫 호출에서
    지연 생성해 이후 요청까지 재사용하며, 일시적 호출 실패로 폐기하지 않는다."""

    def __init__(self) -> None:
        self._client: AsyncOpenAI | None = None
        self._model: str | None = None

    async def _ensure_client(self) -> tuple[AsyncOpenAI, str]:
        if self._client is not None and self._model is not None:
            return self._client, self._model

        api_key, model, base_url = _validate_settings()
        client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=LLM_CALL_TIMEOUT_SECONDS,
            max_retries=LLM_MAX_RETRIES,
        )
        self._client = client
        self._model = model
        return client, model

    async def _create(
        self,
        system_prompt: str,
        user_prompt: str,
        max_completion_tokens: int,
        *,
        json_mode: bool,
    ) -> str:
        client, model = await self._ensure_client()

        kwargs: dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "max_completion_tokens": max_completion_tokens,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        try:
            async with asyncio.timeout(LLM_CALL_TIMEOUT_SECONDS):
                response = await client.chat.completions.create(**kwargs)
        except TimeoutError as exc:
            raise LLMUnavailableError("LLM call timed out", reason="timeout") from exc
        except RateLimitError as exc:
            raise LLMUnavailableError("LLM call was rate limited", reason="rate_limited") from exc
        except OpenAIError as exc:
            raise LLMUnavailableError("LLM call failed", reason="provider_error") from exc

        content = response.choices[0].message.content
        if not content:
            raise LLMUnavailableError("LLM returned an empty response", reason="empty_response")
        return content

    async def complete_json(
        self, system_prompt: str, user_prompt: str, max_completion_tokens: int
    ) -> dict[str, Any]:
        content = await self._create(
            system_prompt, user_prompt, max_completion_tokens, json_mode=True
        )
        return json.loads(content)

    async def complete_text(
        self, system_prompt: str, user_prompt: str, max_completion_tokens: int
    ) -> str:
        return await self._create(
            system_prompt, user_prompt, max_completion_tokens, json_mode=False
        )

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.close()
