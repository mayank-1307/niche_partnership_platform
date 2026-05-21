from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import FileResponse

from app.core.errors import bad_request, upstream_error
from app.core.utils import normalize_domain
from app.models.schemas import AnalyzeRequest, AnalyzeResponse, HealthResponse
from app.services.decision_intelligence_service import decision_intelligence_service
from app.services.orchestrator import analysis_orchestrator
from app.services.storage_service import json_storage_service


router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse()


@router.post("/analyze-company", response_model=AnalyzeResponse)
async def analyze_company(payload: AnalyzeRequest) -> AnalyzeResponse:
    try:
        domain = normalize_domain(payload.domain)
    except ValueError as exc:
        raise bad_request(str(exc)) from exc

    try:
        return await analysis_orchestrator.run(domain)
    except Exception as exc:
        raise upstream_error(str(exc)) from exc


@router.get("/download-json/{file_id}")
async def download_json(file_id: str):
    target = json_storage_service.resolve(file_id)
    if not target.exists():
        raise bad_request("JSON file not found")
    return FileResponse(path=target, media_type="application/json", filename=f"{file_id}.json")


@router.get("/stored-jsons")
async def stored_jsons():
    return {"items": json_storage_service.list_files()}


@router.get("/stored-json/{file_id}")
async def stored_json(file_id: str):
    try:
        return json_storage_service.read(file_id)
    except FileNotFoundError as exc:
        raise bad_request("JSON file not found") from exc


@router.get("/decision-intelligence/{file_id}")
async def decision_intelligence(file_id: str):
    try:
        wrapped = json_storage_service.read(file_id)
    except FileNotFoundError as exc:
        raise bad_request("JSON file not found") from exc

    structured = wrapped.get("data", wrapped)
    if not isinstance(structured, dict):
        raise bad_request("Invalid JSON payload")

    report = decision_intelligence_service.evaluate(structured)
    return {"file_id": file_id, "report": report}
