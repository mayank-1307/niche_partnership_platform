from __future__ import annotations

import json
import logging
from datetime import datetime

from app.models.schemas import AgentLog, GateBasedCompanyAnalysis, ResearchObject, SourceEvidence
from app.services.mistral_client import mistral_client
from app.services.prompts import AGENT2_STRUCTURING_PROMPT

logger = logging.getLogger(__name__)


class JsonStructuringAgent:
    _MAX_SUMMARY_CHARS = 6000
    _MAX_TEXT_FIELD_CHARS = 1200
    _MAX_EVIDENCE_ITEMS = 16
    _DOCUMENT_SECTION_KEYWORDS = {
        "enterprise_credibility": (
            "customer",
            "client",
            "deployment",
            "case stud",
            "funding",
            "investor",
            "round",
            "founder",
            "leadership",
            "executive",
            "headquarter",
            "founded",
            "production",
            "scale",
        ),
        "strategic_relevance": (
            "ai",
            "model",
            "data",
            "automation",
            "governance",
            "compliance",
            "industry",
            "use case",
            "platform",
            "llm",
            "agent",
        ),
        "delivery_feasibility": (
            "integration",
            "api",
            "deployment",
            "implementation",
            "training",
            "support",
            "onboarding",
            "cloud",
            "security",
            "architecture",
        ),
        "commercial_viability": (
            "pricing",
            "revenue",
            "gtm",
            "go-to-market",
            "partner",
            "channel",
            "monetization",
            "contract",
            "deal",
            "sales",
        ),
    }

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

    def _truncate_text(self, value: object, limit: int = _MAX_TEXT_FIELD_CHARS) -> str:
        text = self._to_string(value).strip()
        if len(text) <= limit:
            return text
        return f"{text[:limit].rstrip()}..."

    def _compact_value(self, value: object, *, depth: int = 0) -> object:
        if isinstance(value, str):
            limit = self._MAX_SUMMARY_CHARS if depth == 0 else self._MAX_TEXT_FIELD_CHARS
            return self._truncate_text(value, limit)
        if isinstance(value, list):
            return [self._compact_value(item, depth=depth + 1) for item in value[: self._MAX_EVIDENCE_ITEMS]]
        if isinstance(value, dict):
            return {
                str(key): self._compact_value(item, depth=depth + 1)
                for key, item in value.items()
                if key not in {"document_text", "available_text_excerpt"}
            }
        return value

    def _compact_uploaded_document(self, uploaded_document: dict | None) -> dict | None:
        if not isinstance(uploaded_document, dict):
            return None
        document_extraction = uploaded_document.get("document_extraction")
        compact: dict[str, object] = {
            "filename": self._truncate_text(uploaded_document.get("filename"), 240),
            "content_type": self._truncate_text(uploaded_document.get("content_type"), 120),
            "truncated": bool(uploaded_document.get("truncated")),
        }
        if isinstance(document_extraction, dict):
            compact["document_extraction"] = self._compact_value(document_extraction)
        elif uploaded_document.get("excerpt"):
            compact["excerpt"] = self._truncate_text(uploaded_document.get("excerpt"), 2000)
        return compact

    def _compact_evidence(self, evidence: list[SourceEvidence]) -> list[dict]:
        compact: list[dict] = []
        for item in evidence[: self._MAX_EVIDENCE_ITEMS]:
            compact.append(
                {
                    "url": self._truncate_text(item.url, 500),
                    "title": self._truncate_text(item.title, 240),
                    "snippet": self._truncate_text(item.snippet, 700),
                    "relevance_score": item.relevance_score,
                    "credibility_score": item.credibility_score,
                }
            )
        return compact

    def _uploaded_document_source(self, uploaded_document: dict | None) -> str:
        if not isinstance(uploaded_document, dict):
            return ""
        filename = self._truncate_text(uploaded_document.get("filename") or "uploaded-document", 240)
        content_type = self._truncate_text(uploaded_document.get("content_type"), 120)
        source = f"uploaded-document://{filename}"
        if content_type:
            source = f"{source} ({content_type})"
        return source

    def _document_evidence_items(self, research: ResearchObject) -> list[dict]:
        extraction = research.extracted_insights.get("uploaded_document_extraction")
        if not isinstance(extraction, dict):
            return []
        evidence = extraction.get("document_evidence")
        if not isinstance(evidence, list):
            return []
        return [item for item in evidence if isinstance(item, dict)]

    def _document_sections_for_text(self, text: str) -> set[str]:
        lowered = text.lower()
        sections = {
            section
            for section, keywords in self._DOCUMENT_SECTION_KEYWORDS.items()
            if any(keyword in lowered for keyword in keywords)
        }
        return sections

    def _append_unique_source(self, sources: list[str], source: str) -> list[str]:
        if not source:
            return sources
        existing = {item.strip() for item in sources if item.strip()}
        if source.strip() in existing:
            return sources
        return [*sources, source]

    def _attach_document_sources(
        self,
        model: GateBasedCompanyAnalysis,
        research: ResearchObject,
        logs: list[AgentLog],
    ) -> GateBasedCompanyAnalysis:
        if not research.uploaded_document:
            return model

        document_source = self._uploaded_document_source(research.uploaded_document)
        if not document_source:
            return model

        evidence_items = self._document_evidence_items(research)
        section_sources: dict[str, list[str]] = {
            "enterprise_credibility": [],
            "strategic_relevance": [],
            "delivery_feasibility": [],
            "commercial_viability": [],
        }
        for item in evidence_items:
            fact = self._truncate_text(item.get("fact"), 280)
            excerpt = self._truncate_text(item.get("supporting_excerpt"), 280)
            text = " ".join(part for part in (fact, excerpt) if part)
            source_detail = document_source
            if fact:
                source_detail = f"{document_source} - {fact}"

            for section in self._document_sections_for_text(text):
                section_sources[section].append(source_detail)

        if not any(section_sources.values()):
            for section in section_sources:
                section_sources[section].append(document_source)

        model.enterprise_credibility.sources = self._append_unique_source(
            model.enterprise_credibility.sources,
            document_source,
        )
        for source in section_sources["enterprise_credibility"]:
            model.enterprise_credibility.sources = self._append_unique_source(model.enterprise_credibility.sources, source)
        for source in section_sources["strategic_relevance"]:
            model.strategic_relevance.sources = self._append_unique_source(model.strategic_relevance.sources, source)
        for source in section_sources["delivery_feasibility"]:
            model.delivery_feasibility.sources = self._append_unique_source(model.delivery_feasibility.sources, source)
        for source in section_sources["commercial_viability"]:
            model.commercial_viability.sources = self._append_unique_source(model.commercial_viability.sources, source)

        attached_count = sum(len(values) for values in section_sources.values())
        logs.append(
            AgentLog(
                ts=datetime.utcnow().isoformat(),
                agent="agent_2",
                message=f"Attached uploaded-document evidence to {attached_count} related section source reference(s)",
            )
        )
        logger.info(
            "Agent 2 attached uploaded document sources company=%s source=%s section_counts=%s",
            model.company_name,
            document_source,
            {key: len(value) for key, value in section_sources.items()},
        )
        return model

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
        for key in ("enterprise_credibility", "strategic_relevance", "delivery_feasibility", "gate_3", "commercial_viability"):
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
            "summary_markdown": self._truncate_text(research.summary_markdown, self._MAX_SUMMARY_CHARS),
            "extracted_insights": self._compact_value(research.extracted_insights),
            "confidence_notes": [self._truncate_text(note, 400) for note in research.confidence_notes[:12]],
            "evidence_sources": self._compact_evidence(research.evidence),
        }
        uploaded_document = self._compact_uploaded_document(research.uploaded_document)
        if uploaded_document:
            payload["uploaded_document"] = uploaded_document
            logs.append(
                AgentLog(
                    ts=datetime.utcnow().isoformat(),
                    agent="agent_2",
                    message="Uploaded-document extraction included in structuring payload",
                )
            )
        logger.info(
            "Agent 2 payload prepared company=%s evidence_items=%s uploaded_document=%s",
            research.company_name,
            len(payload["evidence_sources"]),
            bool(uploaded_document),
        )

        llm = await mistral_client.chat_json(
            AGENT2_STRUCTURING_PROMPT,
            json.dumps(payload),
            agent_name="agent2",
        )
        normalized = self._normalize_llm_payload(llm)
        model = GateBasedCompanyAnalysis.model_validate(normalized)
        model = self._attach_document_sources(model, research, logs)
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
