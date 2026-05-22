from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from app.core.utils import to_company_name
from app.models.schemas import AgentLog, ResearchObject, SourceEvidence
from app.services.mistral_client import mistral_client
from app.services.prompts import AGENT1_SUMMARY_PROMPT
from app.services.search_service import search_service


class CompanyIntelligenceAgent:
    def _fallback_summary(self, company_name: str, domain: str, web_hits: list[dict[str, Any]]) -> str:
        lines = [
            f"{company_name} ({domain}) company intelligence summary:",
            "The summary below is synthesized from currently available public web evidence.",
        ]

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

    async def run(self, domain: str, logs: list[AgentLog]) -> ResearchObject:
        company_name = to_company_name(domain)
        logs.append(AgentLog(ts=datetime.utcnow().isoformat(), agent="agent_1", message="Collecting public web verification signals"))
        web_hits = await search_service.search(domain, company_name)

        prompt = {
            "domain": domain,
            "company_name_hint": company_name,
            "web_search": web_hits,
        }

        logs.append(AgentLog(ts=datetime.utcnow().isoformat(), agent="agent_1", message="Summarizing with grounded anti-hallucination rules"))
        try:
            llm = await mistral_client.chat_json(
                AGENT1_SUMMARY_PROMPT,
                json.dumps(prompt),
                agent_name="agent1",
            )
        except Exception:
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

        summary_markdown = (llm.get("summary_markdown") or "").strip()
        if not summary_markdown:
            summary_markdown = self._fallback_summary(company_name, domain, web_hits)

        extracted_insights = llm.get("extracted_insights")
        if not isinstance(extracted_insights, dict) or not extracted_insights:
            extracted_insights = self._fallback_insights(web_hits)

        confidence_notes = llm.get("confidence_notes")
        if not isinstance(confidence_notes, list):
            confidence_notes = []
        if not web_hits:
            confidence_notes = [*confidence_notes, "No web search results were retrieved for this domain in this run."]

        return ResearchObject(
            company_name=llm.get("company_name") or company_name,
            website=domain,
            summary_markdown=summary_markdown,
            extracted_insights=extracted_insights,
            confidence_notes=confidence_notes,
            evidence=evidence[:20],
        )


company_intelligence_agent = CompanyIntelligenceAgent()
