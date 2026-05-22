from __future__ import annotations

from typing import Any

from app.services.llm_agent_runtime import llm_agent_runtime


class MistralClient:
    # Kept class/module naming for backward compatibility with existing imports.
    # Internally this now uses provider-agnostic agent runtime.
    def __init__(self) -> None:
        pass

    async def chat_json(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        agent_name: str = "default",
    ) -> dict[str, Any]:
        return await llm_agent_runtime.run_json(
            agent_name=agent_name,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )


mistral_client = MistralClient()
