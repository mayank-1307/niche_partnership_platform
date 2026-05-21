from __future__ import annotations

from typing import Any


FUNDING_BENCHMARK_USD = 100_000_000


def _as_record(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [x for x in value if isinstance(x, str)]


def _as_number(value: Any) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return 0.0
    return 0.0


class DecisionIntelligenceService:
    def evaluate(self, structured_json: dict[str, Any]) -> dict[str, Any]:
        root = _as_record(structured_json)
        ec = _as_record(root.get("enterprise_credibility"))
        enterprise_customers = _as_record(ec.get("enterprise_customers"))
        funding = _as_record(ec.get("funding"))
        leadership = _as_record(ec.get("leadership"))
        product_maturity = _as_record(ec.get("product_maturity"))
        strategic = _as_record(root.get("strategic_relevance"))

        customers = _as_string_list(enterprise_customers.get("notable_clients"))
        key_leaders = [x.lower() for x in _as_string_list(leadership.get("key_leaders"))]
        funding_total = _as_number(funding.get("total_funding_usd"))
        has_ceo = any("ceo" in x for x in key_leaders)
        has_cto = any("cto" in x for x in key_leaders)
        maturity_stage = product_maturity.get("stage")
        maturity_years = _as_number(product_maturity.get("years_in_market"))
        maturity_case_studies = product_maturity.get("case_studies_available") is True
        maturity_deployment_scale = bool(product_maturity.get("deployment_scale"))

        gate1_enterprise_customers_pass = len(customers) >= 3
        gate1_funding_pass = funding_total >= FUNDING_BENCHMARK_USD
        gate1_leadership_pass = has_ceo and has_cto
        gate1_maturity_pass = bool(maturity_stage) or maturity_years > 0 or maturity_case_studies or maturity_deployment_scale

        gate1_conditions = [
            {
                "label": "Existing enterprise customers (min 3)",
                "pass": gate1_enterprise_customers_pass,
                "logic": (
                    f"Found {len(customers)} notable enterprise clients; minimum required is 3."
                    if gate1_enterprise_customers_pass
                    else f"Found {len(customers)} notable enterprise clients; this is below the minimum 3."
                ),
            },
            {
                "label": f"Recognized funding (>= ${FUNDING_BENCHMARK_USD:,} benchmark)",
                "pass": gate1_funding_pass,
                "logic": (
                    f"Reported funding is ${funding_total:,.0f}, which meets/exceeds the ${FUNDING_BENCHMARK_USD:,.0f} benchmark."
                    if gate1_funding_pass
                    else f"Reported funding is ${funding_total:,.0f}, which is below the ${FUNDING_BENCHMARK_USD:,.0f} benchmark."
                ),
            },
            {
                "label": "Proven leadership team (CEO and CTO)",
                "pass": gate1_leadership_pass,
                "logic": (
                    "Leadership list includes both CEO and CTO roles."
                    if gate1_leadership_pass
                    else "Leadership list does not clearly include both CEO and CTO roles."
                ),
            },
            {
                "label": "Demonstrable product maturity",
                "pass": gate1_maturity_pass,
                "logic": (
                    "Product maturity evidence found (stage/years in market/case studies/deployment scale)."
                    if gate1_maturity_pass
                    else "No clear product maturity evidence found (missing stage, years in market, case studies, and deployment scale)."
                ),
            },
        ]

        gate2_ai_transformation_pass = strategic.get("ai_transformation") is True
        gate2_data_modernization_pass = strategic.get("data_modernization") is True
        gate2_ai_operations_pass = strategic.get("ai_operations") is True
        gate2_conversational_ai_pass = strategic.get("conversational_ai") is True
        gate2_industry_ai_pass = strategic.get("industry_ai") is True
        gate2_governance_compliance_pass = strategic.get("governance_compliance") is True

        gate2_conditions = [
            {
                "label": "AI transformation",
                "pass": gate2_ai_transformation_pass,
                "logic": "Strategic relevance marks AI transformation as true." if gate2_ai_transformation_pass else "Strategic relevance marks AI transformation as false.",
            },
            {
                "label": "Data modernization",
                "pass": gate2_data_modernization_pass,
                "logic": "Strategic relevance marks data modernization as true." if gate2_data_modernization_pass else "Strategic relevance marks data modernization as false.",
            },
            {
                "label": "AI operations",
                "pass": gate2_ai_operations_pass,
                "logic": "Strategic relevance marks AI operations as true." if gate2_ai_operations_pass else "Strategic relevance marks AI operations as false.",
            },
            {
                "label": "Conversational enterprise AI",
                "pass": gate2_conversational_ai_pass,
                "logic": (
                    "Strategic relevance marks conversational AI as true."
                    if gate2_conversational_ai_pass
                    else "Strategic relevance marks conversational AI as false."
                ),
            },
            {
                "label": "Industry AI",
                "pass": gate2_industry_ai_pass,
                "logic": "Strategic relevance marks industry AI as true." if gate2_industry_ai_pass else "Strategic relevance marks industry AI as false.",
            },
            {
                "label": "Governance and compliance",
                "pass": gate2_governance_compliance_pass,
                "logic": (
                    "Strategic relevance marks governance/compliance as true."
                    if gate2_governance_compliance_pass
                    else "Strategic relevance marks governance/compliance as false."
                ),
            },
        ]

        gate1_pass = any(x["pass"] for x in gate1_conditions)
        gate2_pass = any(x["pass"] for x in gate2_conditions)

        return {
            "gate_1": {"name": "Enterprise Credibility", "pass": gate1_pass, "conditions": gate1_conditions},
            "gate_2": {"name": "Strategic Relevance", "pass": gate2_pass, "conditions": gate2_conditions},
            "overall": "PASS" if (gate1_pass and gate2_pass) else "REJECT",
        }


decision_intelligence_service = DecisionIntelligenceService()
