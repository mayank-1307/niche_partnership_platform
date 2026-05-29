from __future__ import annotations

import logging
from datetime import datetime

from app.agents.agent1_company_intelligence import company_intelligence_agent
from app.agents.agent2_json_structuring import json_structuring_agent
from app.models.schemas import AnalyzeResponse, AgentLog
from app.services.db_service import company_profile_db
from app.services.storage_service import json_storage_service

logger = logging.getLogger(__name__)


class CompanyAnalysisOrchestrator:
    async def run(self, domain: str) -> AnalyzeResponse:
        logger.info("Analysis workflow started domain=%s", domain)
        logs: list[AgentLog] = [
            AgentLog(ts=datetime.utcnow().isoformat(), agent="system", message="Starting analysis workflow")
        ]

        # Agent 1 gathers evidence; Agent 2 converts that evidence into the persisted JSON contract.
        research = await company_intelligence_agent.run(domain, logs)
        structured = await json_structuring_agent.run(research, logs)

        if not company_profile_db.enabled:
            logger.error("Analysis workflow blocked because database integration is disabled")
            raise RuntimeError("Database integration is disabled. Set DATABASE_URL to run analysis.")

        structured_payload = structured.model_dump()

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
            structured_json=structured,
            agent_logs=logs,
        )


analysis_orchestrator = CompanyAnalysisOrchestrator()
