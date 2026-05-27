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
  id: number;
  company_name: string | null;
  username: string;
  created_at: string;
};

export type CompanyProfileDetail = {
  id: number;
  company_name: string | null;
  username: string;
  created_at: string;
  artefact: {
    generated_at?: string;
    data?: Record<string, unknown>;
  };
};

export type GateCriterion = { decision: "YES" | "NO"; reason: string };
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
export type DecisionIntelligenceReport = {
  company_name: string;
  gate_1: { status: "PASS" | "FAIL"; criteria: Gate1Criteria };
  gate_2: { status: "PASS" | "FAIL"; criteria: Gate2Criteria };
  overall_partnership_recommendation: {
    priority: "HIGH_PRIORITY" | "MEDIUM_PRIORITY" | "LOW_PRIORITY";
    reason: string;
  };
};

export async function analyzeCompany(domain: string): Promise<AnalyzeResponse> {
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

export async function listCompanyProfiles(): Promise<CompanyProfileSummary[]> {
  const res = await api.get<{ items: CompanyProfileSummary[] }>("/decision-intelligence/profiles");
  return res.data.items ?? [];
}

export async function getCompanyProfile(id: number): Promise<CompanyProfileDetail> {
  const res = await api.get<CompanyProfileDetail>(`/decision-intelligence/profiles/${id}`);
  return res.data;
}
