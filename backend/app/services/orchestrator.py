from __future__ import annotations

import logging
from datetime import datetime

from app.agents.agent_document_intelligence import document_intelligence_agent
from app.agents.agent1_company_intelligence import company_intelligence_agent
from app.agents.agent2_json_structuring import json_structuring_agent
from app.models.schemas import AnalyzeResponse, AgentLog, SourceEvidence
from app.services.document_ingestion_service import UploadedDocumentContext
from app.services.company_json_adapter import gate_company_json_to_legacy_view
from app.services.db_service import company_profile_db
from app.services.storage_service import json_storage_service

logger = logging.getLogger(__name__)


class CompanyAnalysisOrchestrator:
    def _merge_document_intelligence(
        self,
        research_extracted_insights: dict,
        document_payload: dict,
    ) -> dict:
        merged = dict(research_extracted_insights)
        merged["uploaded_document_extraction"] = {
            "document_summary": document_payload.get("document_summary", ""),
            "document_insights": document_payload.get("document_insights", {}),
            "document_evidence": document_payload.get("document_evidence", []),
        }
        return merged

    async def run(self, domain: str, *, uploaded_document: UploadedDocumentContext | None = None) -> AnalyzeResponse:
        logger.info("Analysis workflow started domain=%s", domain)
        logs: list[AgentLog] = [
            AgentLog(ts=datetime.utcnow().isoformat(), agent="system", message="Starting analysis workflow")
        ]
        if uploaded_document is not None:
            logger.info(
                "Analysis workflow received uploaded document domain=%s filename=%s text_chars=%s truncated=%s",
                domain,
                uploaded_document.filename,
                len(uploaded_document.text),
                uploaded_document.truncated,
            )
            logs.append(
                AgentLog(
                    ts=datetime.utcnow().isoformat(),
                    agent="system",
                    message=f"Received uploaded source document {uploaded_document.filename}",
                )
            )

        # Agent 1 gathers web evidence; a document-specific agent extracts uploaded-file facts when available.
        logs.append(AgentLog(ts=datetime.utcnow().isoformat(), agent="system", message="Running Agent 1 company intelligence"))
        research = await company_intelligence_agent.run(domain, logs, uploaded_document=uploaded_document)
        logs.append(
            AgentLog(
                ts=datetime.utcnow().isoformat(),
                agent="system",
                message=f"Agent 1 completed with {len(research.evidence)} evidence source(s)",
            )
        )
        if uploaded_document is not None:
            logs.append(AgentLog(ts=datetime.utcnow().isoformat(), agent="system", message="Running document intelligence agent"))
            document_payload = await document_intelligence_agent.run(uploaded_document, logs)
            document_evidence_count = len(document_payload.get("document_evidence", [])) if isinstance(document_payload.get("document_evidence"), list) else 0
            research.extracted_insights = self._merge_document_intelligence(
                research.extracted_insights,
                document_payload,
            )
            logs.append(
                AgentLog(
                    ts=datetime.utcnow().isoformat(),
                    agent="system",
                    message=f"Merged {document_evidence_count} uploaded-document evidence item(s) into research",
                )
            )
            document_notes = document_payload.get("confidence_notes")
            if isinstance(document_notes, list):
                research.confidence_notes = [
                    *research.confidence_notes,
                    *(str(note).strip() for note in document_notes if str(note).strip()),
                ]
            if isinstance(research.uploaded_document, dict):
                research.uploaded_document["document_extraction"] = document_payload

            for item in document_payload.get("document_evidence", []):
                if not isinstance(item, dict):
                    continue
                fact = str(item.get("fact") or "").strip()
                excerpt = str(item.get("supporting_excerpt") or "").strip()
                research.evidence.insert(
                    0,
                    SourceEvidence(
                        url=str(item.get("source") or f"uploaded-document://{uploaded_document.filename}"),
                        title=f"Uploaded document: {uploaded_document.filename}",
                        snippet=excerpt or fact,
                        relevance_score=0.95,
                        credibility_score=0.95,
                    ),
                )
            logger.info(
                "Analysis workflow merged uploaded document domain=%s evidence_count=%s total_research_evidence=%s",
                domain,
                document_evidence_count,
                len(research.evidence),
            )

        # Agent 2 converts the merged web + document research into the persisted JSON contract.
        logs.append(AgentLog(ts=datetime.utcnow().isoformat(), agent="system", message="Running Agent 2 JSON structuring"))
        structured = await json_structuring_agent.run(research, logs)
        logs.append(AgentLog(ts=datetime.utcnow().isoformat(), agent="system", message="Agent 2 completed JSON structuring"))

        if not company_profile_db.enabled:
            logger.error("Analysis workflow blocked because database integration is disabled")
            raise RuntimeError("Database integration is disabled. Set DATABASE_URL to run analysis.")

        structured_payload = structured.model_dump()
        legacy_structured = gate_company_json_to_legacy_view(
            structured_payload,
            company_summary=research.summary_markdown,
        )

        artefact = {
            "generated_at": datetime.utcnow().isoformat(),
            "company_summary": research.summary_markdown,
            "data": structured_payload,
        }

        logs.append(AgentLog(ts=datetime.utcnow().isoformat(), agent="system", message="Saving analysis to database"))
        profile_id = await company_profile_db.save_company_profile(
            company_name=structured.company_name or research.company_name,
            artefact=artefact,
        )
        logger.info("Analysis saved to database profile_id=%s", profile_id)

        logs.append(AgentLog(ts=datetime.utcnow().isoformat(), agent="system", message="Saving JSON output"))
        file_id = json_storage_service.save(
            structured_payload,
            domain,
            company_name=structured.company_name,
        )
        logger.info("Analysis JSON saved file_id=%s profile_id=%s", file_id, profile_id)

        return AnalyzeResponse(
            id=str(profile_id),
            company_summary=research.summary_markdown,
            extracted_insights=research.extracted_insights,
            evidence=research.evidence,
            structured_json=legacy_structured,
            agent_logs=logs,
        )


analysis_orchestrator = CompanyAnalysisOrchestrator()
