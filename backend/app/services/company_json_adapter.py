from __future__ import annotations

from typing import Any


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _as_str(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _boolish(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        v = value.strip().lower()
        if v in {"true", "yes", "y", "1"}:
            return True
        if v in {"false", "no", "n", "0"}:
            return False
    return default


def _merge_sources(*values: Any) -> list[str]:
    seen: set[str] = set()
    merged: list[str] = []
    for value in values:
        for item in _as_list(value):
            s = _as_str(item)
            if not s or s in seen:
                continue
            seen.add(s)
            merged.append(s)
    return merged


def gate_company_json_to_legacy_view(raw: dict[str, Any], *, company_summary: str = "") -> dict[str, Any]:
    enterprise = _as_dict(raw.get("enterprise_credibility"))
    enterprise_parts = _as_dict(enterprise.get("sub_parts"))
    strategic = _as_dict(raw.get("strategic_relevance"))
    strategic_parts = _as_dict(strategic.get("sub_parts"))
    delivery = _as_dict(raw.get("delivery_feasibility", raw.get("gate_3")))
    delivery_parts = _as_dict(delivery.get("delivery_feasibility"))
    commercial = _as_dict(raw.get("commercial_viability"))
    commercial_parts = _as_dict(commercial.get("sub_parts"))

    enterprise_customers = _as_dict(enterprise_parts.get("existing_enterprise_customers"))
    funding = _as_dict(enterprise_parts.get("institutional_funding"))
    leadership = _as_dict(enterprise_parts.get("proven_leadership_team"))
    product = _as_dict(enterprise_parts.get("production_grade_product_evidence"))

    ai_transformation = _as_dict(strategic_parts.get("ai_transformation_alignment"))
    data_modernization = _as_dict(strategic_parts.get("data_modernization_alignment"))
    ai_operations = _as_dict(strategic_parts.get("ai_operations_alignment"))
    conversational_ai = _as_dict(strategic_parts.get("conversational_ai_alignment"))
    industry_ai = _as_dict(strategic_parts.get("industry_ai_alignment"))
    governance = _as_dict(strategic_parts.get("governance_compliance_alignment"))

    skill_availability = _as_dict(delivery_parts.get("skill_availability"))
    training_effort = _as_dict(delivery_parts.get("training_effort"))
    integration = _as_dict(delivery_parts.get("integration_feasibility"))
    support = _as_dict(delivery_parts.get("support_scalability"))

    monetization = _as_dict(commercial_parts.get("monetization_clarity"))
    gtm = _as_dict(commercial_parts.get("gtm_feasibility"))
    revenue = _as_dict(commercial_parts.get("revenue_upside"))
    partner = _as_dict(commercial_parts.get("partner_willingness"))
    structure = _as_dict(commercial_parts.get("commercial_structure_clarity"))
    stage_fit = _as_dict(commercial_parts.get("startup_stage_fit"))

    enterprise_sources = _merge_sources(enterprise.get("sources"))
    strategic_sources = _merge_sources(strategic.get("sources"))
    delivery_sources = _merge_sources(delivery.get("sources"))
    commercial_sources = _merge_sources(commercial.get("sources"))

    return {
        "company_name": _as_str(raw.get("company_name")),
        "company_summary": _as_str(company_summary),
        "website": _as_str(raw.get("website")),
        "headquarters": _as_str(raw.get("headquarters")),
        "founded_year": raw.get("founded_year") or 0,
        "enterprise_credibility": {
            "enterprise_customers": {
                "has_enterprise_clients": _boolish(enterprise_customers.get("facts", {}).get("has_enterprise_clients")),
                "notable_clients": _as_list(enterprise_customers.get("facts", {}).get("notable_clients")),
            },
            "funding": {
                "is_funded": _boolish(funding.get("facts", {}).get("is_funded")),
                "total_funding_usd": funding.get("facts", {}).get("total_funding_usd") or 0,
                "investors": _as_list(funding.get("facts", {}).get("investors")),
                "recent_rounds": _as_list(funding.get("facts", {}).get("recent_rounds")),
            },
            "leadership": {
                "founders_experience": _as_str(leadership.get("facts", {}).get("founders_experience")),
                "key_leaders": _as_list(leadership.get("facts", {}).get("key_leaders")),
            },
            "product_maturity": {
                "stage": _as_str(product.get("facts", {}).get("stage")),
                "years_in_market": product.get("facts", {}).get("years_in_market") or 0,
                "case_studies_available": _boolish(product.get("facts", {}).get("case_studies_available")),
                "deployment_scale": _as_str(product.get("facts", {}).get("deployment_scale")),
            },
            "sources": enterprise_sources,
        },
        "strategic_relevance": {
            "ai_transformation": _boolish(ai_transformation.get("facts", {}).get("ai_transformation")),
            "data_modernization": _boolish(data_modernization.get("facts", {}).get("data_modernization")),
            "ai_operations": _boolish(ai_operations.get("facts", {}).get("ai_operations")),
            "conversational_ai": _boolish(conversational_ai.get("facts", {}).get("conversational_ai")),
            "industry_ai": _boolish(industry_ai.get("facts", {}).get("industry_ai")),
            "governance_compliance": _boolish(governance.get("facts", {}).get("governance_compliance")),
            "primary_use_cases": _as_list(ai_transformation.get("facts", {}).get("use_cases"))
            or _as_list(strategic.get("primary_use_cases")),
            "sources": strategic_sources,
        },
        "delivery_feasibility": {
            "implementation_complexity": _as_str(skill_availability.get("facts", {}).get("implementation_complexity"))
            or _as_str(delivery.get("facts", {}).get("implementation_complexity")),
            "tcs_implementation_readiness": _as_str(skill_availability.get("facts", {}).get("tcs_implementation_readiness"))
            or _as_str(delivery.get("facts", {}).get("tcs_implementation_readiness")),
            "training_effort_required": _as_str(training_effort.get("facts", {}).get("training_effort_required"))
            or _as_str(delivery.get("facts", {}).get("training_effort_required")),
            "support_scalability": _as_str(support.get("facts", {}).get("support_scalability"))
            or _as_str(delivery.get("support_scalability")),
            "integration_requirements": _as_list(integration.get("facts", {}).get("integration_requirements"))
            or _as_list(delivery.get("integration_requirements")),
            "notes": "",
            "sources": delivery_sources,
        },
        "commercial_viability": {
            "monetization_model": _as_str(monetization.get("facts", {}).get("monetization_model")),
            "pricing_transparency": _boolish(monetization.get("facts", {}).get("pricing_transparency")),
            "gtm_model": _as_str(gtm.get("facts", {}).get("gtm_model")),
            "partner_willingness": _boolish(partner.get("facts", {}).get("partner_willingness")),
            "estimated_deal_size_usd": revenue.get("facts", {}).get("estimated_deal_size_usd") or 0,
            "notes": "",
            "sources": commercial_sources,
        },
        "evidence": {
            "sources": _merge_sources(enterprise_sources, strategic_sources, delivery_sources, commercial_sources),
            "last_updated": _as_str(raw.get("evidence", {}).get("last_updated")) if isinstance(raw.get("evidence"), dict) else "",
        },
    }
