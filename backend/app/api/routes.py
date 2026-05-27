from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import FileResponse

from app.core.errors import bad_request, upstream_error
from app.core.utils import normalize_domain
from app.models.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    CompanyProfileDetail,
    CompanyProfileListResponse,
    HealthResponse,
)
from app.services.db_service import company_profile_db
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
    if target.exists():
        return FileResponse(path=target, media_type="application/json", filename=f"{file_id}.json")

    if file_id.isdigit():
        row = await company_profile_db.get_company_profile(int(file_id))
        artefact = row.get("artefact") if row else None
        if isinstance(artefact, dict):
            body = json.dumps(artefact, ensure_ascii=True, indent=2)
            return Response(
                content=body,
                media_type="application/json",
                headers={"Content-Disposition": f'attachment; filename="{file_id}.json"'},
            )

    raise bad_request("JSON file not found")


@router.get("/stored-jsons")
async def stored_jsons():
    return {"items": json_storage_service.list_files()}


@router.get("/stored-json/{file_id}")
async def stored_json(file_id: str):
    try:
        return json_storage_service.read(file_id)
    except FileNotFoundError as exc:
        raise bad_request("JSON file not found") from exc


@router.get("/decision-intelligence/profiles", response_model=CompanyProfileListResponse)
async def decision_intelligence_profiles() -> CompanyProfileListResponse:
    items = await company_profile_db.list_company_profiles()
    return CompanyProfileListResponse(items=items)


@router.get("/decision-intelligence/profiles/{profile_id}", response_model=CompanyProfileDetail)
async def decision_intelligence_profile(profile_id: int) -> CompanyProfileDetail:
    row = await company_profile_db.get_company_profile(profile_id)
    if not row:
        raise HTTPException(status_code=404, detail="Profile not found")
    return CompanyProfileDetail(**row)


@router.get("/decision-intelligence/{file_id}")
async def decision_intelligence(file_id: str):
    if file_id.isdigit():
        row = await company_profile_db.get_company_profile(int(file_id))
        artefact = row.get("artefact") if row else None
        wrapped = artefact if isinstance(artefact, dict) else None
    else:
        wrapped = None

    if wrapped is None:
        try:
            wrapped = json_storage_service.read(file_id)
        except FileNotFoundError as exc:
            raise bad_request("JSON file not found") from exc

    structured = wrapped.get("data", wrapped)
    if not isinstance(structured, dict):
        raise bad_request("Invalid JSON payload")

    report = await decision_intelligence_service.evaluate(structured)
    return {"file_id": file_id, "report": report}
