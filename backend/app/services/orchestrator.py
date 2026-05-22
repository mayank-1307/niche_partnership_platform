from __future__ import annotations

from datetime import datetime

from app.agents.agent1_company_intelligence import company_intelligence_agent
from app.agents.agent2_json_structuring import json_structuring_agent
from app.models.schemas import AnalyzeResponse, AgentLog
from app.services.storage_service import json_storage_service


class CompanyAnalysisOrchestrator:
    async def run(self, domain: str) -> AnalyzeResponse:
        logs: list[AgentLog] = [
            AgentLog(ts=datetime.utcnow().isoformat(), agent="system", message="Starting analysis workflow")
        ]

        research = await company_intelligence_agent.run(domain, logs)
        structured = await json_structuring_agent.run(research, logs)

        logs.append(AgentLog(ts=datetime.utcnow().isoformat(), agent="system", message="Saving JSON output"))
        file_id = json_storage_service.save(
            structured.model_dump(),
            domain,
            company_name=structured.company_name,
        )

        return AnalyzeResponse(
            id=file_id,
            company_summary=research.summary_markdown,
            extracted_insights=research.extracted_insights,
            evidence=research.evidence,
            structured_json=structured,
            agent_logs=logs,
        )


analysis_orchestrator = CompanyAnalysisOrchestrator()
