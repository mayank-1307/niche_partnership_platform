from __future__ import annotations

import json
from datetime import datetime

from app.models.schemas import AgentLog, CompanyIntelligenceJSON, Evidence, ResearchObject
from app.services.mistral_client import mistral_client
from app.services.prompts import AGENT2_STRUCTURING_PROMPT


class JsonStructuringAgent:
    def _to_string(self, value: object) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value
        if isinstance(value, (int, float, bool)):
            return str(value)
        if isinstance(value, dict):
            for key in ("name", "round", "title", "role", "description"):
                v = value.get(key)
                if isinstance(v, str) and v.strip():
                    return v.strip()
            return json.dumps(value, ensure_ascii=True)
        if isinstance(value, list):
            parts = [self._to_string(x).strip() for x in value]
            parts = [p for p in parts if p]
            return ", ".join(parts)
        return str(value)

    def _coerce_string_list(self, value: object) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            out: list[str] = []
            for item in value:
                s = self._to_string(item).strip()
                if s:
                    out.append(s)
            return out
        s = self._to_string(value).strip()
        return [s] if s else []

    def _normalize_llm_payload(self, llm: dict) -> dict:
        ec = llm.get("enterprise_credibility")
        if not isinstance(ec, dict):
            return llm

        funding = ec.get("funding")
        if isinstance(funding, dict):
            funding["recent_rounds"] = self._coerce_string_list(funding.get("recent_rounds"))

        leadership = ec.get("leadership")
        if isinstance(leadership, dict):
            leadership["key_leaders"] = self._coerce_string_list(leadership.get("key_leaders"))

        return llm

    async def run(self, research: ResearchObject, logs: list[AgentLog]) -> CompanyIntelligenceJSON:
        logs.append(AgentLog(ts=datetime.utcnow().isoformat(), agent="agent_2", message="Structuring strict JSON schema"))
        payload = {
            "company_name": research.company_name,
            "website": research.website,
            "summary_markdown": research.summary_markdown,
            "extracted_insights": research.extracted_insights,
            "confidence_notes": research.confidence_notes,
            "evidence_sources": [e.model_dump() for e in research.evidence],
        }

        llm = await mistral_client.chat_json(AGENT2_STRUCTURING_PROMPT, json.dumps(payload))
        normalized = self._normalize_llm_payload(llm)
        model = CompanyIntelligenceJSON.model_validate(normalized)

        if not model.evidence.sources:
            model.evidence = Evidence(
                sources=[e.url for e in research.evidence if e.url],
                last_updated=datetime.utcnow().isoformat(),
            )
        return model


json_structuring_agent = JsonStructuringAgent()
