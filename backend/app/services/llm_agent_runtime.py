from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Literal

from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings

Provider = Literal["mistral", "gemini"]


@dataclass(frozen=True)
class AgentSpec:
    name: str
    provider: Provider
    model: str


class LLMAgentRuntime:
    def __init__(self) -> None:
        self._clients: dict[Provider, AsyncOpenAI] = {}

    def _provider_from_name(self, raw: str) -> Provider:
        value = (raw or "").strip().lower()
        if value in ("mistral", "gemini"):
            return value  # type: ignore[return-value]
        default_provider = (settings.llm_provider or "mistral").strip().lower()
        if default_provider in ("mistral", "gemini"):
            return default_provider  # type: ignore[return-value]
        return "mistral"

    def _build_spec(self, agent_name: str) -> AgentSpec:
        lower_name = (agent_name or "").strip().lower()
        provider_override = getattr(settings, f"{lower_name}_provider", "") if lower_name else ""
        model_override = getattr(settings, f"{lower_name}_model", "") if lower_name else ""
        provider = self._provider_from_name(provider_override)

        if provider == "mistral":
            model = model_override or settings.llm_model or settings.mistral_model or "mistral-large-latest"
        else:
            model = model_override or settings.gemini_model or "gemini-1.5-flash"
        return AgentSpec(name=agent_name or "default", provider=provider, model=model)

    def _provider_credentials(self, provider: Provider) -> tuple[str, str]:
        if provider == "mistral":
            return settings.mistral_api_key, settings.mistral_base_url
        return settings.gemini_api_key, settings.gemini_base_url

    def _get_client(self, provider: Provider) -> AsyncOpenAI:
        if provider in self._clients:
            return self._clients[provider]

        api_key, base_url = self._provider_credentials(provider)
        self._clients[provider] = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=settings.request_timeout_seconds,
        )
        return self._clients[provider]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8), reraise=True)
    async def run_json(self, *, agent_name: str, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        spec = self._build_spec(agent_name)
        api_key, _ = self._provider_credentials(spec.provider)
        if not api_key:
            raise RuntimeError(f"{spec.provider.upper()} API key missing")

        client = self._get_client(spec.provider)
        response = await client.chat.completions.create(
            model=spec.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        content = response.choices[0].message.content or "{}"
        return json.loads(content)


llm_agent_runtime = LLMAgentRuntime()

