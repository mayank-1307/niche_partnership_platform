from __future__ import annotations

import json
import logging
from datetime import datetime

from app.models.schemas import AgentLog, Evidence, GateBasedCompanyAnalysis, ResearchObject
from app.services.mistral_client import mistral_client
from app.services.prompts import AGENT2_STRUCTURING_PROMPT

logger = logging.getLogger(__name__)


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

        def _normalize_item(value: object) -> dict:
            item = value if isinstance(value, dict) else {}
            facts = item.get("facts") if isinstance(item.get("facts"), dict) else {}
            return {"facts": facts}


        def _normalize_section(section: object, *, container_key: str, item_keys: tuple[str, ...]) -> dict:
            section_dict = section if isinstance(section, dict) else {}
            container = section_dict.get(container_key)
            container_dict = container if isinstance(container, dict) else {}
            normalized_items = {}
            for key in item_keys:
                normalized_items[key] = _normalize_item(container_dict.get(key))
            normalized = dict(section_dict)
            normalized[container_key] = normalized_items
            return normalized

        llm["company_name"] = _as_str(llm.get("company_name"))
        llm["website"] = _as_str(llm.get("website"))
        llm["headquarters"] = _as_str(llm.get("headquarters"))
        try:
            llm["founded_year"] = int(float(llm.get("founded_year") or 0))
        except Exception:
            llm["founded_year"] = 0

        llm["enterprise_credibility"] = _normalize_section(
            llm.get("enterprise_credibility"),
            container_key="sub_parts",
            item_keys=(
                "existing_enterprise_customers",
                "institutional_funding",
                "proven_leadership_team",
                "production_grade_product_evidence",
            ),
        )
        llm["strategic_relevance"] = _normalize_section(
            llm.get("strategic_relevance"),
            container_key="sub_parts",
            item_keys=(
                "ai_transformation_alignment",
                "data_modernization_alignment",
                "ai_operations_alignment",
                "conversational_ai_alignment",
                "industry_ai_alignment",
                "governance_compliance_alignment",
            ),
        )
        llm["delivery_feasibility"] = _normalize_section(
            llm.get("delivery_feasibility", llm.get("gate_3")),
            container_key="delivery_feasibility",
            item_keys=(
                "skill_availability",
                "training_effort",
                "integration_feasibility",
                "support_scalability",
            ),
        )
        llm["commercial_viability"] = _normalize_section(
            llm.get("commercial_viability"),
            container_key="sub_parts",
            item_keys=(
                "monetization_clarity",
                "gtm_feasibility",
                "revenue_upside",
                "partner_willingness",
                "commercial_structure_clarity",
                "startup_stage_fit",
            ),
        )
        for key in ("enterprise_credibility", "strategic_relevance", "gate_3", "commercial_viability"):
            section = llm.get(key)
            if isinstance(section, dict):
                section["sources"] = self._coerce_string_list(section.get("sources"))
        return llm

    async def run(self, research: ResearchObject, logs: list[AgentLog]) -> GateBasedCompanyAnalysis:
        logger.info("Agent 2 started company=%s", research.company_name)
        logs.append(AgentLog(ts=datetime.utcnow().isoformat(), agent="agent_2", message="Structuring strict JSON schema"))
        payload = {
            "company_name": research.company_name,
            "website": research.website,
            "summary_markdown": research.summary_markdown,
            "extracted_insights": research.extracted_insights,
            "confidence_notes": research.confidence_notes,
            "evidence_sources": [e.model_dump() for e in research.evidence],
        }
        if research.uploaded_document:
            payload["uploaded_document"] = research.uploaded_document

        llm = await mistral_client.chat_json(
            AGENT2_STRUCTURING_PROMPT,
            json.dumps(payload),
            agent_name="agent2",
        )
        normalized = self._normalize_llm_payload(llm)
        model = GateBasedCompanyAnalysis.model_validate(normalized)
        logger.info("Agent 2 produced structured gate-based JSON company=%s", model.company_name)
        evidence_sources = [s.strip() for s in self._coerce_string_list(model.evidence.get("sources")) if s.strip()]
        if not evidence_sources:
            logger.warning("Agent 2 JSON had no evidence sources; using fallback sources company=%s", model.company_name)
            model.evidence = {
                "sources": self._fallback_evidence_sources(research),
                "last_updated": datetime.utcnow().isoformat(),
            }
        else:
            model.evidence = {
                **(model.evidence if isinstance(model.evidence, dict) else {}),
                "sources": evidence_sources,
            }
        if research.uploaded_document:
            document_source = f"uploaded-document://{research.uploaded_document.get('filename', 'uploaded-document')}"
            sources = [s.strip() for s in self._coerce_string_list(model.evidence.get("sources")) if s.strip()]
            if document_source not in sources:
                model.evidence = {
                    **(model.evidence if isinstance(model.evidence, dict) else {}),
                    "sources": [document_source, *sources],
                }
        return model


json_structuring_agent = JsonStructuringAgent()
