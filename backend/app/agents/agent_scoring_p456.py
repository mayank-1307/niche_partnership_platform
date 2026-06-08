from __future__ import annotations

import json
import logging
from typing import Any

from app.services.mistral_client import mistral_client
from app.services.prompts import SCORING_PROMPT_P456

logger = logging.getLogger(__name__)


class ScoringP456Agent:
    async def run(self, structured_json: dict[str, Any]) -> dict[str, Any]:
        company_name = str(structured_json.get("company_name") or "").strip()
        logger.info("Scoring P456 agent evaluation started company=%s", company_name)
        return await mistral_client.chat_json(
            SCORING_PROMPT_P456,
            json.dumps({"company_json": structured_json}),
            agent_name="scoring_p456",
        )


scoring_p456_agent = ScoringP456Agent()
