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

export type GateCondition = { label: string; pass: boolean; logic?: string };
export type GateReport = { name: string; pass: boolean; conditions: GateCondition[] };
export type DecisionIntelligenceReport = {
  gate_1: GateReport;
  gate_2: GateReport;
  overall: "PASS" | "REJECT";
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
