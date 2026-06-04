from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

from app.models.schemas import AgentLog
from app.services.document_ingestion_service import UploadedDocumentContext
from app.services.mistral_client import mistral_client
from app.services.prompts import DOCUMENT_EXTRACTION_PROMPT

logger = logging.getLogger(__name__)


class DocumentIntelligenceAgent:
    def _fallback_payload(self, uploaded_document: UploadedDocumentContext) -> dict[str, Any]:
        excerpt = uploaded_document.excerpt.strip()
        return {
            "document_summary": (
                f"Uploaded document {uploaded_document.filename} was provided as a first-party source."
                if excerpt
                else ""
            ),
            "document_insights": {
                "source_document": uploaded_document.filename,
                "available_text_excerpt": excerpt[:4000],
            },
            "document_evidence": [
                {
                    "source": f"uploaded-document://{uploaded_document.filename}",
                    "fact": "Uploaded document text was available for downstream analysis.",
                    "supporting_excerpt": excerpt[:1000],
                    "confidence_score": 50 if excerpt else 0,
                }
            ],
            "confidence_notes": ["Document extraction agent fallback was used; verify document text quality."],
        }

    def _normalize_payload(self, value: Any, uploaded_document: UploadedDocumentContext) -> dict[str, Any]:
        payload = value if isinstance(value, dict) else {}
        document_summary = payload.get("document_summary")
        document_insights = payload.get("document_insights")
        document_evidence = payload.get("document_evidence")
        confidence_notes = payload.get("confidence_notes")

        normalized_evidence: list[dict[str, Any]] = []
        if isinstance(document_evidence, list):
            for item in document_evidence:
                if not isinstance(item, dict):
                    continue
                normalized_evidence.append(
                    {
                        "source": str(item.get("source") or f"uploaded-document://{uploaded_document.filename}").strip(),
                        "fact": str(item.get("fact") or "").strip(),
                        "supporting_excerpt": str(item.get("supporting_excerpt") or "").strip()[:1000],
                        "confidence_score": self._confidence(item.get("confidence_score")),
                    }
                )

        return {
            "document_summary": str(document_summary or "").strip(),
            "document_insights": document_insights if isinstance(document_insights, dict) else {},
            "document_evidence": normalized_evidence,
            "confidence_notes": [str(note).strip() for note in confidence_notes if str(note).strip()]
            if isinstance(confidence_notes, list)
            else [],
        }

    def _confidence(self, value: Any) -> int:
        try:
            confidence = int(round(float(value)))
        except Exception:
            return 0
        return max(0, min(100, confidence))

    async def run(self, uploaded_document: UploadedDocumentContext, logs: list[AgentLog]) -> dict[str, Any]:
        logger.info(
            "Document intelligence started filename=%s text_chars=%s truncated=%s",
            uploaded_document.filename,
            len(uploaded_document.text),
            uploaded_document.truncated,
        )
        logs.append(
            AgentLog(
                ts=datetime.utcnow().isoformat(),
                agent="document_intelligence",
                message=(
                    f"Extracting evidence from uploaded document {uploaded_document.filename} "
                    f"({len(uploaded_document.text)} characters)"
                ),
            )
        )

        prompt = {
            "filename": uploaded_document.filename,
            "content_type": uploaded_document.content_type,
            "document_text": uploaded_document.text,
            "truncated": uploaded_document.truncated,
        }
        try:
            llm = await mistral_client.chat_json(
                DOCUMENT_EXTRACTION_PROMPT,
                json.dumps(prompt),
                agent_name="document_intelligence",
            )
        except Exception:
            logger.exception("Document intelligence failed; using fallback filename=%s", uploaded_document.filename)
            logs.append(
                AgentLog(
                    ts=datetime.utcnow().isoformat(),
                    agent="document_intelligence",
                    message="Document extraction failed, using source excerpt fallback",
                )
            )
            return self._fallback_payload(uploaded_document)

        normalized = self._normalize_payload(llm, uploaded_document)
        if not normalized["document_summary"] and not normalized["document_insights"] and not normalized["document_evidence"]:
            logger.warning("Document intelligence returned no facts; using fallback filename=%s", uploaded_document.filename)
            return self._fallback_payload(uploaded_document)

        logger.info(
            "Document intelligence completed filename=%s evidence_items=%s insight_keys=%s",
            uploaded_document.filename,
            len(normalized["document_evidence"]),
            sorted(normalized["document_insights"].keys()) if isinstance(normalized["document_insights"], dict) else [],
        )
        logs.append(
            AgentLog(
                ts=datetime.utcnow().isoformat(),
                agent="document_intelligence",
                message=f"Extracted {len(normalized['document_evidence'])} document-backed evidence item(s)",
            )
        )
        return normalized


document_intelligence_agent = DocumentIntelligenceAgent()
