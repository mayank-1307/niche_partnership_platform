from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, HttpUrl


class AnalyzeRequest(BaseModel):
    domain: str = Field(..., examples=["https://www.glean.com"])


class AgentLog(BaseModel):
    ts: str
    agent: str
    message: str


class SourceEvidence(BaseModel):
    url: str
    title: str = ""
    snippet: str = ""
    relevance_score: float = 0.0
    credibility_score: float = 0.0


class ResearchObject(BaseModel):
    company_name: str = ""
    website: str = ""
    summary_markdown: str = ""
    extracted_insights: dict[str, Any] = Field(default_factory=dict)
    evidence: list[SourceEvidence] = Field(default_factory=list)
    confidence_notes: list[str] = Field(default_factory=list)


class EnterpriseCustomers(BaseModel):
    has_enterprise_clients: bool = False
    notable_clients: list[str] = Field(default_factory=list)


class Funding(BaseModel):
    is_funded: bool = False
    total_funding_usd: int = 0
    investors: list[str] = Field(default_factory=list)
    recent_rounds: list[str] = Field(default_factory=list)


class Leadership(BaseModel):
    founders_experience: str = ""
    key_leaders: list[str] = Field(default_factory=list)


class ProductMaturity(BaseModel):
    stage: str = ""
    years_in_market: int = 0
    case_studies_available: bool = False
    deployment_scale: str = ""


class EnterpriseCredibility(BaseModel):
    enterprise_customers: EnterpriseCustomers = Field(default_factory=EnterpriseCustomers)
    funding: Funding = Field(default_factory=Funding)
    leadership: Leadership = Field(default_factory=Leadership)
    product_maturity: ProductMaturity = Field(default_factory=ProductMaturity)


class StrategicRelevance(BaseModel):
    ai_transformation: bool = False
    data_modernization: bool = False
    ai_operations: bool = False
    conversational_ai: bool = False
    industry_ai: bool = False
    governance_compliance: bool = False
    primary_use_cases: list[str] = Field(default_factory=list)


class DeliveryFeasibility(BaseModel):
    implementation_complexity: str = ""
    tcs_implementation_readiness: str = ""
    training_effort_required: str = ""
    support_scalability: str = ""
    integration_requirements: list[str] = Field(default_factory=list)
    notes: str = ""


class CommercialViability(BaseModel):
    monetization_model: str = ""
    pricing_transparency: bool = False
    gtm_model: str = ""
    partner_willingness: bool = False
    estimated_deal_size_usd: int = 0
    notes: str = ""


class Evidence(BaseModel):
    sources: list[str] = Field(default_factory=list)
    last_updated: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class CompanyIntelligenceJSON(BaseModel):
    company_name: str = ""
    website: str = ""
    headquarters: str = ""
    founded_year: int = 0
    enterprise_credibility: EnterpriseCredibility = Field(default_factory=EnterpriseCredibility)
    strategic_relevance: StrategicRelevance = Field(default_factory=StrategicRelevance)
    delivery_feasibility: DeliveryFeasibility = Field(default_factory=DeliveryFeasibility)
    commercial_viability: CommercialViability = Field(default_factory=CommercialViability)
    evidence: Evidence = Field(default_factory=Evidence)


class AnalyzeResponse(BaseModel):
    id: str
    company_summary: str
    extracted_insights: dict[str, Any]
    evidence: list[SourceEvidence]
    structured_json: CompanyIntelligenceJSON
    agent_logs: list[AgentLog]


class HealthResponse(BaseModel):
    status: str = "ok"
