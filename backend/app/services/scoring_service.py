from __future__ import annotations

import json
from typing import Any

from app.services.mistral_client import mistral_client
from app.services.prompts import SCORING_PROMPT


class ScoringService:
    async def evaluate(self, structured_json: dict[str, Any]) -> dict[str, Any]:
        llm_report = await mistral_client.chat_json(
            SCORING_PROMPT,
            json.dumps({"company_json": structured_json}),
            agent_name="scoring",
        )
        normalized = self._normalize_report(llm_report, structured_json)
        if not normalized:
            raise RuntimeError("Scoring LLM returned an invalid JSON shape.")
        return normalized

    def _normalize_report(self, raw: dict[str, Any], source_json: dict[str, Any]) -> dict[str, Any] | None:
        if not isinstance(raw, dict):
            return None

        def as_record(value: Any) -> dict[str, Any]:
            return value if isinstance(value, dict) else {}

        def clean_text(value: Any) -> str:
            return str(value).strip() if isinstance(value, str) else ""

        def clean_score(value: Any, *, min_value: int = 0, max_value: int = 5) -> int:
            try:
                n = int(float(value))
            except Exception:
                n = min_value
            return max(min_value, min(max_value, n))

        def clean_float(value: Any) -> float:
            try:
                return float(value)
            except Exception:
                return 0.0

        pillars = as_record(raw.get("pillars"))
        p1 = as_record(pillars.get("p1_domain_solution_depth"))
        p2 = as_record(pillars.get("p2_product_engineering_readiness"))
        p3 = as_record(pillars.get("p3_ai_transparency_trustworthiness"))

        p1_sub = as_record(p1.get("sub_criteria"))
        p2_sub = as_record(p2.get("sub_criteria"))
        p3_sub = as_record(p3.get("sub_criteria"))

        required_p1 = [
            "p1_1_domain_specific_problem_ownership",
            "p1_2_decision_outcome_orientation",
            "p1_3_embedded_domain_logic",
            "p1_4_not_generic_platform_building_block",
            "p1_5_degree_of_workflow_ownership",
        ]
        required_p2 = [
            "p2_1_scalability_performance",
            "p2_2_mlops_maturity",
            "p2_3_security_compliance_readiness",
            "p2_4_deployment_flexibility",
            "p2_5_api_ecosystem_interoperability",
        ]
        required_p3 = [
            "p3_1_explainability_of_outcomes",
            "p3_2_model_transparency",
            "p3_3_bias_hallucination_controls",
            "p3_4_human_in_the_loop_support",
            "p3_5_identity_data_protection",
        ]

        if not all(isinstance(p1_sub.get(key), dict) for key in required_p1):
            return None
        if not all(isinstance(p2_sub.get(key), dict) for key in required_p2):
            return None
        if not all(isinstance(p3_sub.get(key), dict) for key in required_p3):
            return None

        def sub_item(block: dict[str, Any], key: str, *, binary: bool = False) -> dict[str, Any]:
            item = as_record(block.get(key))
            score = clean_score(item.get("score"))
            if binary:
                score = 5 if score >= 3 else 0
            return {"score": score, "reason": clean_text(item.get("reason"))}

        p1_norm_sub = {
            "p1_1_domain_specific_problem_ownership": sub_item(p1_sub, "p1_1_domain_specific_problem_ownership"),
            "p1_2_decision_outcome_orientation": sub_item(p1_sub, "p1_2_decision_outcome_orientation"),
            "p1_3_embedded_domain_logic": sub_item(p1_sub, "p1_3_embedded_domain_logic"),
            "p1_4_not_generic_platform_building_block": sub_item(p1_sub, "p1_4_not_generic_platform_building_block", binary=True),
            "p1_5_degree_of_workflow_ownership": sub_item(p1_sub, "p1_5_degree_of_workflow_ownership"),
        }
        p2_norm_sub = {
            "p2_1_scalability_performance": sub_item(p2_sub, "p2_1_scalability_performance"),
            "p2_2_mlops_maturity": sub_item(p2_sub, "p2_2_mlops_maturity"),
            "p2_3_security_compliance_readiness": sub_item(p2_sub, "p2_3_security_compliance_readiness"),
            "p2_4_deployment_flexibility": sub_item(p2_sub, "p2_4_deployment_flexibility"),
            "p2_5_api_ecosystem_interoperability": sub_item(p2_sub, "p2_5_api_ecosystem_interoperability"),
        }
        p3_norm_sub = {
            "p3_1_explainability_of_outcomes": sub_item(p3_sub, "p3_1_explainability_of_outcomes"),
            "p3_2_model_transparency": sub_item(p3_sub, "p3_2_model_transparency"),
            "p3_3_bias_hallucination_controls": sub_item(p3_sub, "p3_3_bias_hallucination_controls"),
            "p3_4_human_in_the_loop_support": sub_item(p3_sub, "p3_4_human_in_the_loop_support"),
            "p3_5_identity_data_protection": sub_item(p3_sub, "p3_5_identity_data_protection"),
        }

        def average_score(items: dict[str, Any]) -> float:
            values = [float(v["score"]) for v in items.values()]
            return sum(values) / len(values) if values else 0.0

        p1_raw = average_score(p1_norm_sub)
        p2_raw = average_score(p2_norm_sub)
        p3_raw = average_score(p3_norm_sub)

        p1_weight = 25
        p2_weight = 15
        p3_weight = 10

        p1_weighted = (p1_raw / 5.0) * p1_weight
        p2_weighted = (p2_raw / 5.0) * p2_weight
        p3_weighted = (p3_raw / 5.0) * p3_weight
        total = p1_weighted + p2_weighted + p3_weighted

        company_name = str(raw.get("company_name") or source_json.get("company_name") or "").strip()
        normalized = {
            "company_name": company_name,
            "pillars": {
                "p1_domain_solution_depth": {
                    "weight": p1_weight,
                    "raw_score": round(p1_raw, 2),
                    "weighted_score": round(p1_weighted, 2),
                    "summary": clean_text(p1.get("summary")),
                    "sub_criteria": p1_norm_sub,
                },
                "p2_product_engineering_readiness": {
                    "weight": p2_weight,
                    "raw_score": round(p2_raw, 2),
                    "weighted_score": round(p2_weighted, 2),
                    "summary": clean_text(p2.get("summary")),
                    "sub_criteria": p2_norm_sub,
                },
                "p3_ai_transparency_trustworthiness": {
                    "weight": p3_weight,
                    "raw_score": round(p3_raw, 2),
                    "weighted_score": round(p3_weighted, 2),
                    "summary": clean_text(p3.get("summary")),
                    "sub_criteria": p3_norm_sub,
                },
            },
            "total_weighted_score": round(clean_float(raw.get("total_weighted_score")) or total, 2),
            "overall_summary": clean_text(raw.get("overall_summary")),
        }
        return normalized


scoring_service = ScoringService()
