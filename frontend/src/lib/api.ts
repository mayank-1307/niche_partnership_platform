import axios from "axios";

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "http://localhost:8000"
});

export type AgentLog = { ts: string; agent: string; message: string };
export type SourceEvidence = { url: string; title: string; snippet: string; relevance_score: number; credibility_score: number };

export type AnalyzeResponse = {
  id: string;
  company_summary: string;
  extracted_insights: Record<string, unknown>;
  evidence: SourceEvidence[];
  structured_json: Record<string, unknown>;
  agent_logs: AgentLog[];
};

export type StoredJsonItem = {
  id: string;
  filename: string;
  updated_at: string;
};

export type StoredJsonPayload = {
  generated_at?: string;
  data?: Record<string, unknown>;
};

export type CompanyProfileSummary = {
  id: string | number;
  company_name: string | null;
  username: string;
  created_at: string;
};

export type CompanyProfileDetail = {
  id: string | number;
  company_name: string | null;
  username: string;
  created_at: string;
  artefact: {
    generated_at?: string;
    company_summary?: string;
    data?: Record<string, unknown>;
  };
};

export type GateCriterion = { decision: "YES" | "NO"; reason: string; confidence_score: number };
export type Gate3Criterion = { decision: "YES" | "PARTIAL" | "NO" | "HIGH" | "COMPLEX"; reason: string; confidence_score: number };
export type Gate1Criteria = {
  existing_enterprise_customers: GateCriterion;
  institutional_funding: GateCriterion;
  proven_leadership_team: GateCriterion;
  production_grade_product_evidence: GateCriterion;
};
export type Gate2Criteria = {
  ai_transformation_alignment: GateCriterion;
  data_modernization_alignment: GateCriterion;
  ai_operations_alignment: GateCriterion;
  conversational_ai_alignment: GateCriterion;
  industry_ai_alignment: GateCriterion;
  governance_compliance_alignment: GateCriterion;
};
export type Gate3Criteria = {
  skill_availability: Gate3Criterion;
  training_effort: Gate3Criterion;
  integration_feasibility: Gate3Criterion;
  support_scalability: Gate3Criterion;
};
export type Gate4Criteria = {
  monetization_clarity: GateCriterion;
  gtm_feasibility: GateCriterion;
  revenue_upside: GateCriterion;
  partner_willingness: GateCriterion;
  commercial_structure_clarity: GateCriterion;
  startup_stage_fit: GateCriterion;
};
export type Gate5Criteria = {
  restricted_geography: GateCriterion;
  existing_company_x_partnership_conflict: GateCriterion;
};
export type DecisionIntelligenceReport = {
  company_name: string;
  gate_1: { status: "PASS" | "FAIL"; summary: string; criteria: Gate1Criteria };
  gate_2: { status: "PASS" | "FAIL"; summary: string; criteria: Gate2Criteria };
  gate_3: { status: "PASS" | "DEFER" | "FAIL"; summary: string; criteria: Gate3Criteria };
  gate_4: { status: "PASS" | "FAIL"; summary: string; criteria: Gate4Criteria };
  gate_5: { status: "PASS" | "REVIEW" | "FAIL"; summary: string; criteria: Gate5Criteria };
  overall_partnership_recommendation: {
    priority: "HIGH_PRIORITY" | "MEDIUM_PRIORITY" | "LOW_PRIORITY";
    reason: string;
  };
};

export type ScoringSubCriterion = { score: number; reason: string; confidence_score: number };
export type ScoringPillar = {
  weight: number;
  raw_score: number;
  weighted_score: number;
  summary: string;
  sub_criteria: Record<string, ScoringSubCriterion>;
};
export type ScoringReport = {
  company_name: string;
  pillars: {
    p1_domain_solution_depth: ScoringPillar;
    p2_product_engineering_readiness: ScoringPillar;
    p3_ai_transparency_trustworthiness: ScoringPillar;
    p4_business_strategic_fit_for_tcs: ScoringPillar;
    p5_market_validation_feedback: ScoringPillar;
    p6_delivery_readiness_risk: ScoringPillar;
  };
  total_weighted_score: number;
  overall_summary: string;
};

export async function analyzeCompany(domain: string, sourceDocument?: File | null): Promise<AnalyzeResponse> {
  if (sourceDocument) {
    const formData = new FormData();
    formData.append("domain", domain);
    formData.append("document", sourceDocument);
    const res = await api.post<AnalyzeResponse>("/analyze-company", formData);
    return res.data;
  }

  const res = await api.post<AnalyzeResponse>("/analyze-company", { domain });
  return res.data;
}

export function downloadJsonUrl(id: string): string {
  return `${api.defaults.baseURL}/download-json/${id}`;
}

export async function listStoredJsons(): Promise<StoredJsonItem[]> {
  const res = await api.get<{ items: StoredJsonItem[] }>("/stored-jsons");
  return res.data.items ?? [];
}

export async function getStoredJson(fileId: string): Promise<StoredJsonPayload> {
  const res = await api.get<StoredJsonPayload>(`/stored-json/${fileId}`);
  return res.data;
}

export async function getDecisionIntelligenceReport(fileId: string): Promise<DecisionIntelligenceReport> {
  const res = await api.get<{ file_id: string; report: DecisionIntelligenceReport }>(`/decision-intelligence/${fileId}`);
  return res.data.report;
}

export async function listCompanyProfiles(query = ""): Promise<CompanyProfileSummary[]> {
  const res = await api.get<{ items: CompanyProfileSummary[] }>("/decision-intelligence/profiles", {
    params: query.trim() ? { q: query.trim() } : undefined,
  });
  return res.data.items ?? [];
}

export async function getCompanyProfile(id: string | number): Promise<CompanyProfileDetail> {
  const res = await api.get<CompanyProfileDetail>(`/decision-intelligence/profiles/${id}`);
  return res.data;
}

export async function getScoringReport(fileId: string): Promise<ScoringReport> {
  const res = await api.get<{ file_id: string; report: ScoringReport }>(`/scoring/${fileId}`);
  return res.data.report;
}
