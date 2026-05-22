from __future__ import annotations

import json
from datetime import datetime

from app.models.schemas import AgentLog, CompanyIntelligenceJSON, Evidence, ResearchObject
from app.services.mistral_client import mistral_client
from app.services.prompts import AGENT2_STRUCTURING_PROMPT


class JsonStructuringAgent:
    def _fallback_evidence_sources(self, research: ResearchObject) -> list[str]:
        out: list[str] = []
        seen: set[str] = set()

        for e in research.evidence:
            candidates = [
                (e.url or "").strip(),
                (e.title or "").strip(),
                (e.snippet or "").strip(),
            ]
            for value in candidates:
                if not value:
                    continue
                if value in seen:
                    continue
                seen.add(value)
                out.append(value)

        website = (research.website or "").strip()
        if website and website not in seen:
            out.append(website)

        return out

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
        def _as_str(value: object) -> str:
            return self._to_string(value).strip()

        ec = llm.get("enterprise_credibility")
        if not isinstance(ec, dict):
            ec = {}
            llm["enterprise_credibility"] = ec

        funding = ec.get("funding")
        if isinstance(funding, dict):
            funding["recent_rounds"] = self._coerce_string_list(funding.get("recent_rounds"))

        leadership = ec.get("leadership")
        if isinstance(leadership, dict):
            leadership["key_leaders"] = self._coerce_string_list(leadership.get("key_leaders"))

        df = llm.get("delivery_feasibility")
        if isinstance(df, dict):
            for key in (
                "implementation_complexity",
                "tcs_implementation_readiness",
                "training_effort_required",
                "support_scalability",
                "notes",
            ):
                if key in df:
                    df[key] = _as_str(df.get(key))
            df["integration_requirements"] = self._coerce_string_list(df.get("integration_requirements"))

        cv = llm.get("commercial_viability")
        if isinstance(cv, dict):
            for key in ("monetization_model", "gtm_model", "notes"):
                if key in cv:
                    cv[key] = _as_str(cv.get(key))

        evidence = llm.get("evidence")
        if isinstance(evidence, dict):
            evidence["sources"] = self._coerce_string_list(evidence.get("sources"))
            if "last_updated" in evidence:
                evidence["last_updated"] = _as_str(evidence.get("last_updated"))

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

        llm = await mistral_client.chat_json(
            AGENT2_STRUCTURING_PROMPT,
            json.dumps(payload),
            agent_name="agent2",
        )
        normalized = self._normalize_llm_payload(llm)
        model = CompanyIntelligenceJSON.model_validate(normalized)

        model_sources = [s.strip() for s in model.evidence.sources if isinstance(s, str) and s.strip()]
        if not model_sources:
            model.evidence = Evidence(
                sources=self._fallback_evidence_sources(research),
                last_updated=datetime.utcnow().isoformat(),
            )
        else:
            model.evidence.sources = model_sources
        return model


json_structuring_agent = JsonStructuringAgent()
