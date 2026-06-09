from __future__ import annotations

import json
import logging
import uuid
from email import policy
from email.parser import BytesParser

from fastapi import APIRouter, HTTPException, Query, Request, Response
from fastapi.responses import FileResponse

from app.core.errors import bad_request, upstream_error
from app.core.utils import normalize_domain
from app.models.schemas import (
    AnalyzeResponse,
    CompanyProfileDetail,
    CompanyProfileListResponse,
    HealthResponse,
)
from app.services.company_json_adapter import gate_company_json_to_legacy_view
from app.services.document_ingestion_service import UploadedDocumentContext, extract_uploaded_document
from app.services.db_service import company_profile_db
from app.services.decision_intelligence_service import decision_intelligence_service
from app.services.orchestrator import analysis_orchestrator
from app.services.scoring_service import scoring_service
from app.services.storage_service import json_storage_service


router = APIRouter()
logger = logging.getLogger(__name__)


def _extract_profile_id(file_id: str) -> str | int | None:
    if file_id.isdigit():
        return int(file_id)
    try:
        uuid.UUID(file_id)
        return file_id
    except ValueError:
        return None


async def _parse_multipart_analysis_request(request: Request) -> tuple[str, UploadedDocumentContext | None]:
    content_type = request.headers.get("content-type", "")
    raw_body = await request.body()
    if not raw_body:
        raise bad_request("Uploaded form data is empty.")

    message = BytesParser(policy=policy.default).parsebytes(
        b"Content-Type: " + content_type.encode("utf-8", errors="ignore") + b"\r\n\r\n" + raw_body
    )
    if not message.is_multipart():
        raise bad_request("Invalid uploaded form data.")

    domain = ""
    uploaded_document: UploadedDocumentContext | None = None

    for part in message.iter_parts():
        field_name = part.get_param("name", header="content-disposition")
        if not field_name:
            continue

        if field_name == "domain":
            domain = part.get_content().strip()
            continue

        filename = part.get_filename()
        if field_name == "document" and filename:
            payload = part.get_payload(decode=True) or b""
            try:
                uploaded_document = extract_uploaded_document(
                    filename=filename,
                    content_type=part.get_content_type(),
                    data=payload,
                )
            except ValueError as exc:
                raise bad_request(str(exc)) from exc

    return domain, uploaded_document


async def _parse_analysis_request(request: Request) -> tuple[str, UploadedDocumentContext | None]:
    content_type = request.headers.get("content-type", "").lower()
    if content_type.startswith("multipart/form-data"):
        return await _parse_multipart_analysis_request(request)

    try:
        payload = await request.json()
    except Exception as exc:
        raise bad_request("Invalid JSON analysis request") from exc

    if not isinstance(payload, dict):
        raise bad_request("Invalid analysis request")
    return str(payload.get("domain") or "").strip(), None


async def _persist_report(file_id: str, evaluation_type: str, report: dict, row_exists: bool) -> None:
    profile_id = _extract_profile_id(file_id)
    if profile_id is None or not row_exists:
        logger.debug(
            "Skipping evaluation report persistence file_id=%s evaluation_type=%s",
            file_id,
            evaluation_type,
        )
        return

    try:
        report_id = await company_profile_db.save_evaluation_report(
            profile_id=profile_id,
            evaluation_type=evaluation_type,
            report_json=report,
        )
        logger.info(
            "Saved evaluation report file_id=%s evaluation_type=%s report_id=%s",
            file_id,
            evaluation_type,
            report_id,
        )
    except Exception:
        logger.exception(
            "Failed to persist evaluation report file_id=%s evaluation_type=%s",
            file_id,
            evaluation_type,
        )


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse()


@router.post("/analyze-company", response_model=AnalyzeResponse)
async def analyze_company(request: Request) -> AnalyzeResponse:
    try:
        domain, uploaded_document = await _parse_analysis_request(request)
        domain = normalize_domain(domain)
    except ValueError as exc:
        logger.warning("Invalid analysis domain submitted")
        raise bad_request(str(exc)) from exc

    try:
        logger.info("Starting company analysis for domain=%s", domain)
        return await analysis_orchestrator.run(domain, uploaded_document=uploaded_document)
    except Exception as exc:
        logger.exception("Company analysis failed for domain=%s", domain)
        raise upstream_error(str(exc)) from exc


@router.get("/download-json/{file_id}")
async def download_json(file_id: str):
    target = json_storage_service.resolve(file_id)
    if target.exists():
        logger.info("Serving stored JSON file_id=%s from disk", file_id)
        return FileResponse(path=target, media_type="application/json", filename=f"{file_id}.json")

    profile_id = _extract_profile_id(file_id)
    if profile_id is not None:
        row = await company_profile_db.get_company_profile(profile_id)
        artefact = row.get("artefact") if row else None
        if isinstance(artefact, dict):
            logger.info("Serving stored JSON file_id=%s from database", file_id)
            body = json.dumps(artefact, ensure_ascii=True, indent=2)
            return Response(
                content=body,
                media_type="application/json",
                headers={"Content-Disposition": f'attachment; filename="{file_id}.json"'},
            )

    raise bad_request("JSON file not found")


@router.get("/stored-jsons")
async def stored_jsons():
    logger.debug("Listing disk-stored JSON outputs")
    return {"items": json_storage_service.list_files()}


@router.get("/stored-json/{file_id}")
async def stored_json(file_id: str):
    try:
        return json_storage_service.read(file_id)
    except FileNotFoundError as exc:
        raise bad_request("JSON file not found") from exc


@router.get("/decision-intelligence/profiles", response_model=CompanyProfileListResponse)
async def decision_intelligence_profiles(
    q: str = Query(default="", description="Optional company name or website search term"),
) -> CompanyProfileListResponse:
    logger.debug("Listing company profiles q=%s", q)
    items = await company_profile_db.list_company_profiles(search=q, limit=5)
    return CompanyProfileListResponse(items=items)


@router.get("/decision-intelligence/profiles/{profile_id}", response_model=CompanyProfileDetail)
async def decision_intelligence_profile(profile_id: str) -> CompanyProfileDetail:
    parsed_id = _extract_profile_id(profile_id)
    if parsed_id is None:
        raise HTTPException(status_code=400, detail="Invalid profile identifier format")
        
    row = await company_profile_db.get_company_profile(parsed_id)
    if not row:
        logger.warning("Company profile not found profile_id=%s", profile_id)
        raise HTTPException(status_code=404, detail="Profile not found")

    artefact = row.get("artefact") if isinstance(row, dict) else None
    if isinstance(artefact, dict) and isinstance(artefact.get("data"), dict):
        row = dict(row)
        row["artefact"] = {
            **artefact,
            "data": gate_company_json_to_legacy_view(
                artefact.get("data", {}),
                company_summary=str(artefact.get("company_summary") or ""),
            ),
        }
    return CompanyProfileDetail(**row)


@router.get("/decision-intelligence/{file_id}")
async def decision_intelligence(file_id: str):
    logger.info("Generating decision intelligence file_id=%s", file_id)
    # Numeric or UUID IDs are database profiles; other IDs refer to disk JSON exports.
    row_exists = False
    profile_id = _extract_profile_id(file_id)
    if profile_id is not None:
        row = await company_profile_db.get_company_profile(profile_id)
        artefact = row.get("artefact") if row else None
        wrapped = artefact if isinstance(artefact, dict) else None
        row_exists = row is not None
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
    await _persist_report(file_id, "decision_intelligence", report, row_exists)
    logger.info("Decision intelligence generated file_id=%s", file_id)
    return {"file_id": file_id, "report": report}


@router.get("/scoring/{file_id}")
async def scoring(file_id: str):
    logger.info("Generating scoring report file_id=%s", file_id)
    # Numeric or UUID IDs are database profiles; other IDs refer to disk JSON exports.
    row_exists = False
    profile_id = _extract_profile_id(file_id)
    if profile_id is not None:
        row = await company_profile_db.get_company_profile(profile_id)
        artefact = row.get("artefact") if row else None
        wrapped = artefact if isinstance(artefact, dict) else None
        row_exists = row is not None
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

    report = await scoring_service.evaluate(structured)
    await _persist_report(file_id, "scoring", report, row_exists)
    logger.info("Scoring report generated file_id=%s", file_id)
    return {"file_id": file_id, "report": report}
