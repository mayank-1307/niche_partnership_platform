from __future__ import annotations

import json
from typing import Any

from app.services.mistral_client import mistral_client
from app.services.prompts import DECISION_INTELLIGENCE_PROMPT

class DecisionIntelligenceService:
    async def evaluate(self, structured_json: dict[str, Any]) -> dict[str, Any]:
        llm_report = await mistral_client.chat_json(
            DECISION_INTELLIGENCE_PROMPT,
            json.dumps({"company_json": structured_json}),
            agent_name="decision_intelligence",
        )
        normalized = self._normalize_report(llm_report, structured_json)
        if not normalized:
            top_level = list(llm_report.keys()) if isinstance(llm_report, dict) else []
            raise RuntimeError(
                f"Decision Intelligence LLM returned an invalid JSON shape. Top-level keys: {top_level}"
            )
        return normalized

    def _normalize_report(self, raw: dict[str, Any], source_json: dict[str, Any]) -> dict[str, Any] | None:
        if not isinstance(raw, dict):
            return None

        def as_record(value: Any) -> dict[str, Any]:
            return value if isinstance(value, dict) else {}

        def clean_decision(value: Any) -> str:
            return "YES" if str(value).strip().upper() == "YES" else "NO"

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
        g1c = as_record(gate_1.get("criteria"))
        g2c = as_record(gate_2.get("criteria"))
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

        # Reject partial/misaligned LLM payloads so fallback logic can handle scoring.
        if not all(get_key_ci(g1c, key) for key in required_g1):
            return None
        if not all(get_key_ci(g2c, key) for key in required_g2):
            return None

        def criterion(block: dict[str, Any], key: str) -> dict[str, str]:
            item = as_record(get_key_ci(block, key))
            return {"decision": clean_decision(item.get("decision")), "reason": clean_reason(item.get("reason"))}

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
            "overall_partnership_recommendation": {
                "priority": clean_priority(overall.get("priority")),
                "reason": clean_reason(overall.get("reason")),
            },
        }
        if not normalized["overall_partnership_recommendation"]["priority"]:
            return None
        return normalized


decision_intelligence_service = DecisionIntelligenceService()
