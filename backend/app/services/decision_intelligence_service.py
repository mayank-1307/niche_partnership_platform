from __future__ import annotations

import json
import logging
from typing import Any

from app.services.mistral_client import mistral_client
from app.services.prompts import DECISION_INTELLIGENCE_PROMPT

logger = logging.getLogger(__name__)

class DecisionIntelligenceService:
    async def evaluate(self, structured_json: dict[str, Any]) -> dict[str, Any]:
        company_name = str(structured_json.get("company_name") or "").strip()
        logger.info("Decision intelligence evaluation started company=%s", company_name)
        llm_report = await mistral_client.chat_json(
            DECISION_INTELLIGENCE_PROMPT,
            json.dumps({"company_json": structured_json}),
            agent_name="decision_intelligence",
        )
        normalized = self._normalize_report(llm_report, structured_json)
        if not normalized:
            top_level = list(llm_report.keys()) if isinstance(llm_report, dict) else []
            logger.error("Decision intelligence invalid shape company=%s keys=%s", company_name, top_level)
            raise RuntimeError(
                f"Decision Intelligence LLM returned an invalid JSON shape. Top-level keys: {top_level}"
            )
        logger.info("Decision intelligence evaluation completed company=%s", normalized.get("company_name", company_name))
        return normalized

    def _normalize_report(self, raw: dict[str, Any], source_json: dict[str, Any]) -> dict[str, Any] | None:
        if not isinstance(raw, dict):
            return None

        def as_record(value: Any) -> dict[str, Any]:
            return value if isinstance(value, dict) else {}

        def clean_decision(value: Any, allowed: tuple[str, ...] = ("YES", "NO")) -> str:
            v = str(value).strip().upper()
            return v if v in allowed else allowed[-1]

        def clean_reason(value: Any) -> str:
            return str(value).strip() if isinstance(value, str) and value.strip() else ""

        def clean_priority(value: Any) -> str:
            v = str(value).strip().upper()
            if v in ("HIGH_PRIORITY", "MEDIUM_PRIORITY", "LOW_PRIORITY"):
                return v
            return ""

        def get_key_ci(block: dict[str, Any], expected_key: str) -> dict[str, Any]:
            if expected_key in block and isinstance(block.get(expected_key), dict):
                return block[expected_key]
            expected = expected_key.lower()
            for k, v in block.items():
                if isinstance(k, str) and k.lower() == expected and isinstance(v, dict):
                    return v
            return {}

        company_name = str(raw.get("company_name") or source_json.get("company_name") or "").strip()
        gate_1 = as_record(raw.get("gate_1"))
        gate_2 = as_record(raw.get("gate_2"))
        gate_3 = as_record(raw.get("gate_3"))
        gate_4 = as_record(raw.get("gate_4"))
        g1c = as_record(gate_1.get("criteria"))
        g2c = as_record(gate_2.get("criteria"))
        g3c = as_record(gate_3.get("criteria"))
        g4c = as_record(gate_4.get("criteria"))
        overall = as_record(raw.get("overall_partnership_recommendation"))

        required_g1 = [
            "existing_enterprise_customers",
            "institutional_funding",
            "proven_leadership_team",
            "production_grade_product_evidence",
        ]
        required_g2 = [
            "ai_transformation_alignment",
            "data_modernization_alignment",
            "ai_operations_alignment",
            "conversational_ai_alignment",
            "industry_ai_alignment",
            "governance_compliance_alignment",
        ]
        required_g3 = [
            "skill_availability",
            "training_effort",
            "integration_feasibility",
            "support_scalability",
        ]
        required_g4 = [
            "monetization_clarity",
            "gtm_feasibility",
            "revenue_upside",
            "partner_willingness",
            "commercial_structure_clarity",
            "startup_stage_fit",
        ]

        # Reject partial/misaligned LLM payloads before status normalization.
        if not all(get_key_ci(g1c, key) for key in required_g1):
            return None
        if not all(get_key_ci(g2c, key) for key in required_g2):
            return None
        if not all(get_key_ci(g3c, key) for key in required_g3):
            return None
        if not all(get_key_ci(g4c, key) for key in required_g4):
            return None

        def criterion(block: dict[str, Any], key: str, allowed: tuple[str, ...] = ("YES", "NO")) -> dict[str, str]:
            item = as_record(get_key_ci(block, key))
            return {"decision": clean_decision(item.get("decision"), allowed=allowed), "reason": clean_reason(item.get("reason"))}

        normalized = {
            "company_name": company_name,
            "gate_1": {
                "status": "PASS" if str(gate_1.get("status")).strip().upper() == "PASS" else "FAIL",
                "criteria": {
                    "existing_enterprise_customers": criterion(g1c, "existing_enterprise_customers"),
                    "institutional_funding": criterion(g1c, "institutional_funding"),
                    "proven_leadership_team": criterion(g1c, "proven_leadership_team"),
                    "production_grade_product_evidence": criterion(g1c, "production_grade_product_evidence"),
                },
            },
            "gate_2": {
                "status": "PASS" if str(gate_2.get("status")).strip().upper() == "PASS" else "FAIL",
                "criteria": {
                    "ai_transformation_alignment": criterion(g2c, "ai_transformation_alignment"),
                    "data_modernization_alignment": criterion(g2c, "data_modernization_alignment"),
                    "ai_operations_alignment": criterion(g2c, "ai_operations_alignment"),
                    "conversational_ai_alignment": criterion(g2c, "conversational_ai_alignment"),
                    "industry_ai_alignment": criterion(g2c, "industry_ai_alignment"),
                    "governance_compliance_alignment": criterion(g2c, "governance_compliance_alignment"),
                },
            },
            "gate_3": {
                "status": str(gate_3.get("status")).strip().upper()
                if str(gate_3.get("status")).strip().upper() in ("PASS", "DEFER", "FAIL")
                else "FAIL",
                "criteria": {
                    "skill_availability": criterion(g3c, "skill_availability", allowed=("YES", "PARTIAL", "NO")),
                    "training_effort": criterion(g3c, "training_effort", allowed=("YES", "HIGH", "NO")),
                    "integration_feasibility": criterion(g3c, "integration_feasibility", allowed=("YES", "COMPLEX", "NO")),
                    "support_scalability": criterion(g3c, "support_scalability", allowed=("YES", "PARTIAL", "NO")),
                },
            },
            "gate_4": {
                "status": "PASS" if str(gate_4.get("status")).strip().upper() == "PASS" else "FAIL",
                "criteria": {
                    "monetization_clarity": criterion(g4c, "monetization_clarity"),
                    "gtm_feasibility": criterion(g4c, "gtm_feasibility"),
                    "revenue_upside": criterion(g4c, "revenue_upside"),
                    "partner_willingness": criterion(g4c, "partner_willingness"),
                    "commercial_structure_clarity": criterion(g4c, "commercial_structure_clarity"),
                    "startup_stage_fit": criterion(g4c, "startup_stage_fit"),
                },
            },
            "overall_partnership_recommendation": {
                "priority": clean_priority(overall.get("priority")),
                "reason": clean_reason(overall.get("reason")),
            },
        }
        if not normalized["overall_partnership_recommendation"]["priority"]:
            return None
        return normalized


decision_intelligence_service = DecisionIntelligenceService()
