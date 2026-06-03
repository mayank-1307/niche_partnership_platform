from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

from app.core.utils import to_company_name
from app.models.schemas import AgentLog, ResearchObject, SourceEvidence
from app.services.document_ingestion_service import UploadedDocumentContext
from app.services.mistral_client import mistral_client
from app.services.prompts import AGENT1_SUMMARY_PROMPT
from app.services.search_service import search_service

logger = logging.getLogger(__name__)


class CompanyIntelligenceAgent:
    def _fallback_summary(
        self,
        company_name: str,
        domain: str,
        web_hits: list[dict[str, Any]],
        uploaded_document: UploadedDocumentContext | None = None,
    ) -> str:
        lines = [
            f"{company_name} ({domain}) company intelligence summary:",
            "The summary below is synthesized from currently available public web evidence.",
        ]

        if uploaded_document is not None:
            lines.append(
                f"- Uploaded document source: {uploaded_document.filename} "
                f"({uploaded_document.content_type or 'unknown type'})"
            )
            preview_lines = uploaded_document.excerpt.splitlines()
            if preview_lines:
                lines.append(f"- Document excerpt: {preview_lines[0][:320]}")

        for hit in web_hits[:10]:
            title = (hit.get("title") or "").strip()
            snippet = (hit.get("snippet") or "").strip()
            url = (hit.get("url") or "").strip()
            if not (title or snippet or url):
                continue
            point = " - ".join(x for x in [title, snippet] if x)
            if url:
                point = f"{point} ({url})" if point else url
            lines.append(f"- {point}")

        if len(lines) <= 2:
            lines.append("- Limited public evidence was retrieved for this domain in this run.")
            lines.append("- Retrying may provide richer data depending on search index freshness.")

        return "\n".join(lines[:15])

    def _fallback_insights(self, web_hits: list[dict[str, Any]]) -> dict[str, Any]:
        snippets = [(h.get("snippet") or "").strip() for h in web_hits if (h.get("snippet") or "").strip()]
        return {
            "company_overview": snippets[:3],
            "products_services": [],
            "ai_capabilities": [],
            "enterprise_customers": [],
            "funding": [],
            "leadership": [],
            "partnerships": [],
            "industry_focus": [],
            "integrations": [],
            "business_model": [],
            "technical_maturity": [],
            "headquarters": "",
            "founded_year": "",
        }

    async def run(
        self,
        domain: str,
        logs: list[AgentLog],
        *,
        uploaded_document: UploadedDocumentContext | None = None,
    ) -> ResearchObject:
        company_name = to_company_name(domain)
        logger.info("Agent 1 started domain=%s company_hint=%s", domain, company_name)
        logs.append(AgentLog(ts=datetime.utcnow().isoformat(), agent="agent_1", message="Collecting public web verification signals"))
        web_hits = await search_service.search(domain, company_name)
        logger.info("Agent 1 collected web signals domain=%s hits=%s", domain, len(web_hits))

        prompt = {
            "domain": domain,
            "company_name_hint": company_name,
            "web_search": web_hits,
        }
        if uploaded_document is not None:
            prompt["uploaded_document"] = {
                "filename": uploaded_document.filename,
                "content_type": uploaded_document.content_type,
                "text_excerpt": uploaded_document.excerpt,
                "truncated": uploaded_document.truncated,
            }

        logs.append(AgentLog(ts=datetime.utcnow().isoformat(), agent="agent_1", message="Summarizing with grounded anti-hallucination rules"))
        try:
            llm = await mistral_client.chat_json(
                AGENT1_SUMMARY_PROMPT,
                json.dumps(prompt),
                agent_name="agent1",
            )
        except Exception:
            logger.exception("Agent 1 LLM summary failed; using fallback synthesis domain=%s", domain)
            llm = {}
            logs.append(AgentLog(ts=datetime.utcnow().isoformat(), agent="agent_1", message="LLM summary failed, using fallback synthesis"))

        evidence = [
            SourceEvidence(
                url=hit.get("url", ""),
                title=hit.get("title", ""),
                snippet=hit.get("snippet", ""),
                relevance_score=0.75,
                credibility_score=0.7,
            )
            for hit in web_hits
            if hit.get("url")
        ]
        if uploaded_document is not None:
            evidence.insert(
                0,
                SourceEvidence(
                    url=f"uploaded-document://{uploaded_document.filename}",
                    title=uploaded_document.filename,
                    snippet=uploaded_document.excerpt[:1000],
                    relevance_score=0.95,
                    credibility_score=0.95,
                ),
            )

        summary_markdown = (llm.get("summary_markdown") or "").strip()
        if not summary_markdown:
            logger.warning("Agent 1 summary missing from LLM output; using fallback domain=%s", domain)
            summary_markdown = self._fallback_summary(company_name, domain, web_hits, uploaded_document)

        extracted_insights = llm.get("extracted_insights")
        if not isinstance(extracted_insights, dict) or not extracted_insights:
            logger.warning("Agent 1 insights missing from LLM output; using fallback domain=%s", domain)
            extracted_insights = self._fallback_insights(web_hits)

        confidence_notes = llm.get("confidence_notes")
        if not isinstance(confidence_notes, list):
            confidence_notes = []
        if not web_hits:
            confidence_notes = [*confidence_notes, "No web search results were retrieved for this domain in this run."]
        if uploaded_document is not None and uploaded_document.truncated:
            confidence_notes = [*confidence_notes, "Uploaded document text was truncated before LLM analysis."]

        uploaded_document_payload = None
        if uploaded_document is not None:
            uploaded_document_payload = {
                "filename": uploaded_document.filename,
                "content_type": uploaded_document.content_type,
                "text_excerpt": uploaded_document.excerpt,
                "truncated": uploaded_document.truncated,
            }

        return ResearchObject(
            company_name=llm.get("company_name") or company_name,
            website=domain,
            summary_markdown=summary_markdown,
            extracted_insights=extracted_insights,
            confidence_notes=confidence_notes,
            evidence=evidence[:20],
            uploaded_document=uploaded_document_payload,
        )


company_intelligence_agent = CompanyIntelligenceAgent()
