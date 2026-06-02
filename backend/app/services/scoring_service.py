from __future__ import annotations

import json
import logging
from typing import Any

from app.services.mistral_client import mistral_client
from app.services.prompts import SCORING_PROMPT, SCORING_PROMPT_P456

logger = logging.getLogger(__name__)


class ScoringService:
    async def evaluate(self, structured_json: dict[str, Any]) -> dict[str, Any]:
        company_name = str(structured_json.get("company_name") or "").strip()
        logger.info("Scoring evaluation started company=%s", company_name)
        report_p123 = await mistral_client.chat_json(
            SCORING_PROMPT,
            json.dumps({"company_json": structured_json}),
            agent_name="scoring_p123",
        )
        report_p456 = await mistral_client.chat_json(
            SCORING_PROMPT_P456,
            json.dumps({"company_json": structured_json}),
            agent_name="scoring_p456",
        )
        llm_report = self._merge_reports(report_p123, report_p456, structured_json)
        normalized = self._normalize_report(llm_report, structured_json)
        if not normalized:
            top_level = list(llm_report.keys()) if isinstance(llm_report, dict) else []
            logger.error("Scoring invalid shape company=%s keys=%s", company_name, top_level)
            raise RuntimeError("Scoring LLM returned an invalid JSON shape.")
        logger.info("Scoring evaluation completed company=%s total=%s", normalized.get("company_name", company_name), normalized.get("total_weighted_score"))
        return normalized

    def _merge_reports(self, report_p123: dict[str, Any], report_p456: dict[str, Any], source_json: dict[str, Any]) -> dict[str, Any]:
        def as_record(value: Any) -> dict[str, Any]:
            return value if isinstance(value, dict) else {}

        def clean_text(value: Any) -> str:
            return str(value).strip() if isinstance(value, str) else ""

        p123 = as_record(report_p123)
        p456 = as_record(report_p456)
        p123_pillars = as_record(p123.get("pillars"))
        p456_pillars = as_record(p456.get("pillars"))

        merged_pillars: dict[str, Any] = {}
        merged_pillars["p1_domain_solution_depth"] = p123_pillars.get("p1_domain_solution_depth", {})
        merged_pillars["p2_product_engineering_readiness"] = p123_pillars.get("p2_product_engineering_readiness", {})
        merged_pillars["p3_ai_transparency_trustworthiness"] = p123_pillars.get("p3_ai_transparency_trustworthiness", {})
        merged_pillars["p4_business_strategic_fit_for_tcs"] = p456_pillars.get("p4_business_strategic_fit_for_tcs", {})
        merged_pillars["p5_market_validation_feedback"] = p456_pillars.get("p5_market_validation_feedback", {})
        merged_pillars["p6_delivery_readiness_risk"] = p456_pillars.get("p6_delivery_readiness_risk", {})

        summary_parts = [
            clean_text(p123.get("overall_summary")),
            clean_text(p456.get("overall_summary")),
        ]
        overall_summary = " ".join(part for part in summary_parts if part)
        company_name = clean_text(p123.get("company_name")) or clean_text(p456.get("company_name")) or clean_text(source_json.get("company_name"))

        return {
            "company_name": company_name,
            "pillars": merged_pillars,
            "total_weighted_score": 0,
            "overall_summary": overall_summary,
        }

    def _normalize_report(self, raw: dict[str, Any], source_json: dict[str, Any]) -> dict[str, Any] | None:
        if not isinstance(raw, dict):
            return None

        def as_record(value: Any) -> dict[str, Any]:
            return value if isinstance(value, dict) else {}

        def clean_text(value: Any) -> str:
            return str(value).strip() if isinstance(value, str) else ""

        def clean_confidence(value: Any) -> int:
            try:
                raw_confidence = float(value)
            except Exception:
                return 0

            if 0.0 <= raw_confidence <= 1.0:
                confidence = int(round(raw_confidence * 100))
            else:
                confidence = int(round(raw_confidence))

            return max(0, min(100, confidence))

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
        p4 = as_record(pillars.get("p4_business_strategic_fit_for_tcs"))
        p5 = as_record(pillars.get("p5_market_validation_feedback"))
        p6 = as_record(pillars.get("p6_delivery_readiness_risk"))

        p1_sub = as_record(p1.get("sub_criteria"))
        p2_sub = as_record(p2.get("sub_criteria"))
        p3_sub = as_record(p3.get("sub_criteria"))
        p4_sub = as_record(p4.get("sub_criteria"))
        p5_sub = as_record(p5.get("sub_criteria"))
        p6_sub = as_record(p6.get("sub_criteria"))

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
        required_p4 = [
            "p4_1_cost_transparency",
            "p4_2_measurable_roi",
            "p4_3_value_capture_for_tcs",
            "p4_4_ip_ownership_clarity",
            "p4_5_scalability_via_tcs",
            "p4_6_strategic_ai_alignment",
            "p4_7_future_trajectory",
            "p4_8_time_to_value",
        ]
        required_p5 = [
            "p5_1_analyst_recognition",
            "p5_2_market_sentiment",
            "p5_3_customer_references_discrete",
            "p5_4_active_deal_pipeline_discrete",
        ]
        required_p6 = [
            "p6_1_skill_availability",
            "p6_2_training_effort",
            "p6_3_integration_complexity",
            "p6_4_delivery_risk_discrete",
            "p6_5_data_dependency_readiness",
            "p6_6_number_of_employees",
        ]

        if not all(isinstance(p1_sub.get(key), dict) for key in required_p1):
            return None
        if not all(isinstance(p2_sub.get(key), dict) for key in required_p2):
            return None
        if not all(isinstance(p3_sub.get(key), dict) for key in required_p3):
            return None
        p4_present = all(isinstance(p4_sub.get(key), dict) for key in required_p4)
        p5_present = all(isinstance(p5_sub.get(key), dict) for key in required_p5)
        p6_present = all(isinstance(p6_sub.get(key), dict) for key in required_p6)

        def sub_item(
            block: dict[str, Any],
            key: str,
            *,
            binary: bool = False,
            discrete: str | None = None,
        ) -> dict[str, Any]:
            item = as_record(block.get(key))
            score = clean_score(item.get("score"))
            if binary:
                score = 5 if score >= 3 else 0
            elif discrete == "three_level_530":
                score = 5 if score >= 4 else 3 if score >= 2 else 0
            elif discrete == "four_level_5310":
                score = 5 if score >= 4 else 3 if score >= 2 else 1 if score >= 1 else 0
            return {
                "score": score,
                "reason": clean_text(item.get("reason")),
                "confidence_score": clean_confidence(item.get("confidence_score")),
            }

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
        p4_norm_sub = {
            "p4_1_cost_transparency": sub_item(p4_sub, "p4_1_cost_transparency"),
            "p4_2_measurable_roi": sub_item(p4_sub, "p4_2_measurable_roi"),
            "p4_3_value_capture_for_tcs": sub_item(p4_sub, "p4_3_value_capture_for_tcs"),
            "p4_4_ip_ownership_clarity": sub_item(p4_sub, "p4_4_ip_ownership_clarity", binary=True),
            "p4_5_scalability_via_tcs": sub_item(p4_sub, "p4_5_scalability_via_tcs"),
            "p4_6_strategic_ai_alignment": sub_item(p4_sub, "p4_6_strategic_ai_alignment"),
            "p4_7_future_trajectory": sub_item(p4_sub, "p4_7_future_trajectory"),
            "p4_8_time_to_value": sub_item(p4_sub, "p4_8_time_to_value"),
        }
        p5_norm_sub = {
            "p5_1_analyst_recognition": sub_item(p5_sub, "p5_1_analyst_recognition"),
            "p5_2_market_sentiment": sub_item(p5_sub, "p5_2_market_sentiment"),
            "p5_3_customer_references_discrete": sub_item(p5_sub, "p5_3_customer_references_discrete", discrete="three_level_530"),
            "p5_4_active_deal_pipeline_discrete": sub_item(p5_sub, "p5_4_active_deal_pipeline_discrete", discrete="four_level_5310"),
        }
        p6_norm_sub = {
            "p6_1_skill_availability": sub_item(p6_sub, "p6_1_skill_availability"),
            "p6_2_training_effort": sub_item(p6_sub, "p6_2_training_effort"),
            "p6_3_integration_complexity": sub_item(p6_sub, "p6_3_integration_complexity"),
            "p6_4_delivery_risk_discrete": sub_item(p6_sub, "p6_4_delivery_risk_discrete", discrete="four_level_5310"),
            "p6_5_data_dependency_readiness": sub_item(p6_sub, "p6_5_data_dependency_readiness"),
            "p6_6_number_of_employees": sub_item(p6_sub, "p6_6_number_of_employees"),
        }

        def average_score(items: dict[str, Any]) -> float:
            values = [float(v["score"]) for v in items.values()]
            return sum(values) / len(values) if values else 0.0

        def disabled_pillar(weight: int, sub_criteria: dict[str, Any], summary: str) -> dict[str, Any]:
            return {
                "weight": weight,
                "raw_score": 0.0,
                "weighted_score": 0.0,
                "summary": summary,
                "sub_criteria": sub_criteria,
            }

        p1_raw = average_score(p1_norm_sub)
        p2_raw = average_score(p2_norm_sub)
        p3_raw = average_score(p3_norm_sub)
        p4_raw = average_score(p4_norm_sub)
        p5_raw = average_score(p5_norm_sub)
        p6_raw = average_score(p6_norm_sub)

        p1_weight = 25
        p2_weight = 15
        p3_weight = 10
        p4_weight = 20
        p5_weight = 15
        p6_weight = 15

        p1_weighted = (p1_raw / 5.0) * p1_weight
        p2_weighted = (p2_raw / 5.0) * p2_weight
        p3_weighted = (p3_raw / 5.0) * p3_weight
        p4_weighted = (p4_raw / 5.0) * p4_weight
        p5_weighted = (p5_raw / 5.0) * p5_weight
        p6_weighted = (p6_raw / 5.0) * p6_weight
        total = p1_weighted + p2_weighted + p3_weighted + p4_weighted + p5_weighted + p6_weighted

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
                "p4_business_strategic_fit_for_tcs": (
                    {
                        "weight": p4_weight,
                        "raw_score": round(p4_raw, 2),
                        "weighted_score": round(p4_weighted, 2),
                        "summary": clean_text(p4.get("summary")),
                        "sub_criteria": p4_norm_sub,
                    }
                    if p4_present
                    else disabled_pillar(
                        p4_weight,
                        {
                            "p4_1_cost_transparency": {"score": 0, "reason": "Disabled for first-three-pillar test.", "confidence_score": 0},
                            "p4_2_measurable_roi": {"score": 0, "reason": "Disabled for first-three-pillar test.", "confidence_score": 0},
                            "p4_3_value_capture_for_tcs": {"score": 0, "reason": "Disabled for first-three-pillar test.", "confidence_score": 0},
                            "p4_4_ip_ownership_clarity": {"score": 0, "reason": "Disabled for first-three-pillar test.", "confidence_score": 0},
                            "p4_5_scalability_via_tcs": {"score": 0, "reason": "Disabled for first-three-pillar test.", "confidence_score": 0},
                            "p4_6_strategic_ai_alignment": {"score": 0, "reason": "Disabled for first-three-pillar test.", "confidence_score": 0},
                            "p4_7_future_trajectory": {"score": 0, "reason": "Disabled for first-three-pillar test.", "confidence_score": 0},
                            "p4_8_time_to_value": {"score": 0, "reason": "Disabled for first-three-pillar test.", "confidence_score": 0},
                        },
                        "Temporarily disabled for first-three-pillar test.",
                    )
                ),
                "p5_market_validation_feedback": (
                    {
                        "weight": p5_weight,
                        "raw_score": round(p5_raw, 2),
                        "weighted_score": round(p5_weighted, 2),
                        "summary": clean_text(p5.get("summary")),
                        "sub_criteria": p5_norm_sub,
                    }
                    if p5_present
                    else disabled_pillar(
                        p5_weight,
                        {
                            "p5_1_analyst_recognition": {"score": 0, "reason": "Disabled for first-three-pillar test.", "confidence_score": 0},
                            "p5_2_market_sentiment": {"score": 0, "reason": "Disabled for first-three-pillar test.", "confidence_score": 0},
                            "p5_3_customer_references_discrete": {"score": 0, "reason": "Disabled for first-three-pillar test.", "confidence_score": 0},
                            "p5_4_active_deal_pipeline_discrete": {"score": 0, "reason": "Disabled for first-three-pillar test.", "confidence_score": 0},
                        },
                        "Temporarily disabled for first-three-pillar test.",
                    )
                ),
                "p6_delivery_readiness_risk": (
                    {
                        "weight": p6_weight,
                        "raw_score": round(p6_raw, 2),
                        "weighted_score": round(p6_weighted, 2),
                        "summary": clean_text(p6.get("summary")),
                        "sub_criteria": p6_norm_sub,
                    }
                    if p6_present
                    else disabled_pillar(
                        p6_weight,
                        {
                            "p6_1_skill_availability": {"score": 0, "reason": "Disabled for first-three-pillar test.", "confidence_score": 0},
                            "p6_2_training_effort": {"score": 0, "reason": "Disabled for first-three-pillar test.", "confidence_score": 0},
                            "p6_3_integration_complexity": {"score": 0, "reason": "Disabled for first-three-pillar test.", "confidence_score": 0},
                            "p6_4_delivery_risk_discrete": {"score": 0, "reason": "Disabled for first-three-pillar test.", "confidence_score": 0},
                            "p6_5_data_dependency_readiness": {"score": 0, "reason": "Disabled for first-three-pillar test.", "confidence_score": 0},
                            "p6_6_number_of_employees": {"score": 0, "reason": "Disabled for first-three-pillar test.", "confidence_score": 0},
                        },
                        "Temporarily disabled for first-three-pillar test.",
                    )
                ),
            },
            "total_weighted_score": round(total, 2),
            "overall_summary": clean_text(raw.get("overall_summary")),
        }
        return normalized


scoring_service = ScoringService()
