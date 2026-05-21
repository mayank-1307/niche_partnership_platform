from __future__ import annotations

import json
from typing import Any

from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings


class MistralClient:
    # Kept class/module naming for backward compatibility with existing imports.
    def __init__(self) -> None:
        self.api_key = settings.mistral_api_key
        self.model = settings.mistral_model or "mistral-large-latest"
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=settings.mistral_base_url,
            timeout=settings.request_timeout_seconds,
        )

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8), reraise=True)
    async def chat_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        if not self.api_key:
            raise RuntimeError("MISTRAL_API_KEY missing")

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        content = response.choices[0].message.content or "{}"
        return json.loads(content)


mistral_client = MistralClient()
