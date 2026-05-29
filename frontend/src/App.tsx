import { motion } from "framer-motion";
import { Brain, ShieldCheck, Sparkles } from "lucide-react";
import { useEffect, useState } from "react";
import toast, { Toaster } from "react-hot-toast";
import { Link } from "react-router-dom";

import { FixedHeader } from "./components/FixedHeader";
import { JsonViewer } from "./components/JsonViewer";
import {
  analyzeCompany,
  downloadJsonUrl,
  getCompanyProfile,
  listCompanyProfiles,
  type AnalyzeResponse,
  type CompanyProfileSummary,
} from "./lib/api";

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" ? (value as Record<string, unknown>) : {};
}

function asStringList(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.filter((item): item is string => typeof item === "string" && item.trim().length > 0);
}

function yesNo(value: unknown): string {
  return value === true ? "Yes" : value === false ? "No" : "-";
}

function asNumber(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string" && value.trim() !== "") {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

function formatUsd(value: unknown): string {
  const amount = asNumber(value);
  if (amount === null) return "-";
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(amount);
}

export default function App() {
  const [domain, setDomain] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AnalyzeResponse | null>(null);
  const [inputLocked, setInputLocked] = useState(false);
  const [expandedInsightBlocks, setExpandedInsightBlocks] = useState<Record<string, boolean>>({});
  const [recentProfiles, setRecentProfiles] = useState<CompanyProfileSummary[]>([]);
  const [loadingRecentProfiles, setLoadingRecentProfiles] = useState(false);

  useEffect(() => {
    const loadRecentProfiles = async () => {
      setLoadingRecentProfiles(true);
      try {
        const items = await listCompanyProfiles();
        setRecentProfiles(items.slice(0, 5));
      } catch (error: any) {
        toast.error(error?.response?.data?.detail || "Failed to load recent searches");
      } finally {
        setLoadingRecentProfiles(false);
      }
    };
    void loadRecentProfiles();
  }, []);

  const run = async () => {
    if (!domain.trim()) {
      toast.error("Enter a company domain");
      return;
    }

    setInputLocked(true);
    setLoading(true);
    setResult(null);
    try {
      const res = await analyzeCompany(domain);
      setResult(res);
      toast.success("Analysis complete");
      localStorage.setItem("company-intel-last", JSON.stringify(res));
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || "Analysis failed");
    } finally {
      setLoading(false);
    }
  };

  const refreshForNewAnalysis = () => {
    window.location.reload();
  };

  const toggleInsightBlock = (blockId: string) => {
    setExpandedInsightBlocks((prev) => ({ ...prev, [blockId]: !prev[blockId] }));
  };

  const loadRecentAnalysis = async (profileId: number) => {
    setLoading(true);
    try {
      const profile = await getCompanyProfile(profileId);
      const structured = profile.artefact?.data;
      if (!structured || typeof structured !== "object") {
        toast.error("Saved profile data is invalid");
        return;
      }
      const savedSummary =
        typeof structured.company_summary === "string" && structured.company_summary.trim()
          ? structured.company_summary
          : profile.artefact?.company_summary || `Loaded from saved analysis (${new Date(profile.created_at).toLocaleString()}).`;

      setResult({
        id: String(profile.id),
        company_summary: savedSummary,
        extracted_insights: {},
        evidence: [],
        structured_json: structured,
        agent_logs: [],
      });
      setInputLocked(true);
      toast.success("Loaded saved analysis from database");
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || "Failed to load saved analysis");
    } finally {
      setLoading(false);
    }
  };

  const structured = asRecord(result?.structured_json);
  const enterprise = asRecord(structured.enterprise_credibility);
  const funding = asRecord(enterprise.funding);
  const leadership = asRecord(enterprise.leadership);
  const productMaturity = asRecord(enterprise.product_maturity);
  const strategic = asRecord(structured.strategic_relevance);
  const delivery = asRecord(structured.delivery_feasibility);
  const commercial = asRecord(structured.commercial_viability);
  const useCases = asStringList(strategic.primary_use_cases);
  const integrationReqs = asStringList(delivery.integration_requirements);
  const investors = asStringList(funding.investors);
  const rounds = asStringList(funding.recent_rounds);
  const leaders = asStringList(leadership.key_leaders);
  const evidence = asRecord(structured.evidence);
  const evidenceSources = asStringList(evidence.sources);
  const evidenceLastUpdated = typeof evidence.last_updated === "string" ? evidence.last_updated.trim() : "";
  const companyName = typeof structured.company_name === "string" ? structured.company_name.trim() : "";
  const hasCompanyName = Boolean(result && companyName);

  return (
    <>
      <FixedHeader />
      <div className="mx-auto max-w-7xl px-4 pb-8 pt-24 md:px-8">
      <Toaster position="top-right" />

{/* header section */}
      <motion.section initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="mb-8">
        <div className="glass rounded-3xl p-8">
          <div className="mb-4 flex items-center justify-between gap-4">
            <h1 className="text-3xl font-bold md:text-5xl">Partner Analysis</h1>
            <Link to="/" className="rounded-lg border border-white/20 px-4 py-2 text-sm hover:bg-white/10">
            Home
            </Link>
          </div>
          <p className="mt-3 max-w-3xl text-slate-300">Single-click deep partner company research with two specialized AI agents, evidence tracing, and strict JSON export.</p>
        </div>
      </motion.section>


      <section className="glass mb-8 rounded-2xl p-4 md:p-6">
        <div className="flex flex-col gap-3 md:flex-row">
          <input
            value={domain}
            onChange={(e) => setDomain(e.target.value)}
            placeholder="Please enter the company domain (e.g., https://company.com)"
            disabled={inputLocked}
            className="w-full rounded-xl border border-white/10 bg-black/30 px-4 py-3 outline-none focus:border-cyan/50"
          />
          <button onClick={run} disabled={loading || !domain.trim()} className="rounded-xl bg-gradient-to-r from-cyan to-indigo px-6 py-3 font-semibold text-black disabled:opacity-60">
            {loading ? "Analyzing..." : "Analyze"}
          </button>
          <button
            type="button"
            onClick={refreshForNewAnalysis}
            disabled={loading}
            className="rounded-xl border border-white/20 bg-black/30 px-6 py-3 font-semibold text-white disabled:opacity-60"
          >
            Reset
          </button>
        </div>
        <p className="mt-3 text-xs text-slate-400">
          **The agents are accessing data from the official sites as well as publicly available sources**
        </p>
        <div className="mt-4">
          <div className="mb-2 text-sm text-cyan">Recent 5 Searches</div>
          {loadingRecentProfiles ? (
            <div className="text-xs text-slate-400">Loading recent searches...</div>
          ) : recentProfiles.length === 0 ? (
            <div className="text-xs text-slate-400">No recent searches found.</div>
          ) : (
            <div className="flex flex-wrap gap-2">
              {recentProfiles.map((profile) => (
                <button
                  key={profile.id}
                  type="button"
                  onClick={() => void loadRecentAnalysis(profile.id)}
                  disabled={loading}
                  className="rounded-lg border border-white/20 bg-black/30 px-3 py-2 text-xs text-slate-200 hover:bg-white/10 disabled:opacity-60"
                >
                  {(profile.company_name || `Profile ${profile.id}`).trim()} ({new Date(profile.created_at).toLocaleDateString()})
                </button>
              ))}
            </div>
          )}
        </div>
      </section>

      <div className="grid grid-cols-1 items-stretch gap-6 lg:grid-cols-2">
        <div className="flex flex-col gap-6 lg:h-full lg:min-h-0">
          <div className="glass flex flex-col rounded-2xl p-5 lg:min-h-0 lg:flex-1">
            <div className="mb-3 flex items-center gap-2 text-sm text-cyan">
              <span>Company Summary</span>
              {hasCompanyName && <span className="text-2xl font-bold">{companyName}</span>}
            </div>
            <div className="prose prose-invert max-w-none whitespace-pre-wrap text-sm text-slate-200 lg:min-h-0 lg:overflow-auto">{result?.company_summary || "Summary will appear after extraction."}</div>
          </div>

          {evidenceSources.length > 0 && (
            <div className="glass flex flex-col rounded-2xl p-5 lg:min-h-0 lg:flex-1">
              <div className="mb-3 flex items-center gap-2 text-sm text-cyan">Sources</div>
              <div className="space-y-2 lg:min-h-0 lg:overflow-auto">
                {evidenceSources.map((source, index) => {
                  const isUrl = /^https?:\/\//i.test(source);

                  return (
                    <div key={`${source}-${index}`} className="rounded-lg border border-white/10 bg-black/20 p-3 text-sm text-slate-200">
                      {isUrl ? (
                        <a href={source} target="_blank" rel="noreferrer" className="break-words text-cyan hover:text-white">
                          {source}
                        </a>
                      ) : (
                        <span className="break-words">{source}</span>
                      )}
                    </div>
                  );
                })}
              </div>
              {evidenceLastUpdated && <div className="mt-3 text-xs text-slate-400">Last updated: {evidenceLastUpdated}</div>}
            </div>
          )}
        </div>

        <JsonViewer data={result?.structured_json ?? null} downloadUrl={result ? downloadJsonUrl(result.id) : null} companyName={companyName} />
      </div>

      <section className="mt-6 space-y-4">
        <div className="glass rounded-2xl p-5">
          <div className="mb-4 flex items-center gap-2 text-sm text-cyan">
            Key Insights Dashboard
          </div>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-2">
            <div className="max-h-64 overflow-auto rounded-xl border border-white/10 bg-black/20 p-4">
              <div className="sticky top-0 z-10 -mx-4 mb-2 flex items-center justify-between gap-2 border-b border-white/10 bg-slate-900 px-4 py-2">
                <div className="text-sm uppercase tracking-wide text-slate-400">Enterprise Credibility</div>
                <button
                  type="button"
                  onClick={() => toggleInsightBlock("company_funding_key_players")}
                  className="rounded-md border border-white/20 px-2 py-1 text-xs font-semibold text-slate-200 hover:bg-white/10"
                >
                  {expandedInsightBlocks.company_funding_key_players ? "Hide" : "Detail"}
                </button>
              </div>
              {expandedInsightBlocks.company_funding_key_players && (
                <div className="pt-1">
                  <div className="mt-2 text-base font-semibold text-white">{String(structured.company_name ?? "-")}</div>
                  <div className="mt-1 text-sm text-slate-400">{String(structured.website ?? "-")}</div>
                  <div className="mt-3 text-sm text-slate-300">Headquarters: {String(structured.headquarters ?? "-")}</div>
                  <div className="text-sm text-slate-300">Founded: {String(structured.founded_year ?? "-")}</div>
                  <div className="mt-3 text-sm text-slate-300">Funded: {yesNo(funding.is_funded)}</div>
                  <div className="text-sm text-slate-300">Total Funding (USD): {formatUsd(funding.total_funding_usd)}</div>
                  <div className="mt-2 text-sm text-slate-400">Investors</div>
                  <div className="mt-1 text-sm">{investors.length ? investors.join(", ") : "-"}</div>
                  <div className="mt-2 text-sm text-slate-400">Recent Rounds</div>
                  <div className="mt-1 text-sm">{rounds.length ? rounds.join(", ") : "-"}</div>
                  <div className="mt-3 text-sm text-slate-300">Founders Experience: {String(leadership.founders_experience ?? "-")}</div>
                  <div className="mt-2 text-sm text-slate-400">Key Leaders</div>
                  <div className="mt-1 text-sm">{leaders.length ? leaders.join(", ") : "-"}</div>
                  <div className="mt-2 text-sm text-slate-300">Stage: {String(productMaturity.stage ?? "-")}</div>
                  <div className="text-sm text-slate-300">Years in Market: {String(productMaturity.years_in_market ?? "-")}</div>
                </div>
              )}
            </div>

            <div className="max-h-64 overflow-auto rounded-xl border border-white/10 bg-black/20 p-4">
              <div className="sticky top-0 z-10 -mx-4 mb-2 flex items-center justify-between gap-2 border-b border-white/10 bg-slate-900 px-4 py-2">
                <div className="text-sm uppercase tracking-wide text-slate-400">Strategic Relevance</div>
                <button
                  type="button"
                  onClick={() => toggleInsightBlock("strategic_relevance")}
                  className="rounded-md border border-white/20 px-2 py-1 text-xs font-semibold text-slate-200 hover:bg-white/10"
                >
                  {expandedInsightBlocks.strategic_relevance ? "Hide" : "Detail"}
                </button>
              </div>
              {expandedInsightBlocks.strategic_relevance && (
                <div className="pt-1">
                  <div className="mt-2 grid grid-cols-2 gap-2 text-sm">
                    <div>AI Transformation: {yesNo(strategic.ai_transformation)}</div>
                    <div>Data Modernization: {yesNo(strategic.data_modernization)}</div>
                    <div>AI Operations: {yesNo(strategic.ai_operations)}</div>
                    <div>Conversational AI: {yesNo(strategic.conversational_ai)}</div>
                    <div>Industry AI: {yesNo(strategic.industry_ai)}</div>
                    <div>Compliance: {yesNo(strategic.governance_compliance)}</div>
                  </div>
                  <div className="mt-3 text-sm text-slate-400">Primary Use Cases</div>
                  <div className="mt-1 text-sm">{useCases.length ? useCases.join(", ") : "-"}</div>
                </div>
              )}
            </div>

            <div className="max-h-64 overflow-auto rounded-xl border border-white/10 bg-black/20 p-4">
              <div className="sticky top-0 z-10 -mx-4 mb-2 flex items-center justify-between gap-2 border-b border-white/10 bg-slate-900 px-4 py-2">
                <div className="text-sm uppercase tracking-wide text-slate-400">Delivery Feasibility</div>
                <button
                  type="button"
                  onClick={() => toggleInsightBlock("delivery_feasibility")}
                  className="rounded-md border border-white/20 px-2 py-1 text-xs font-semibold text-slate-200 hover:bg-white/10"
                >
                  {expandedInsightBlocks.delivery_feasibility ? "Hide" : "Detail"}
                </button>
              </div>
              {expandedInsightBlocks.delivery_feasibility && (
                <div className="pt-1">
                  <div className="mt-2 text-sm text-slate-300">Complexity: {String(delivery.implementation_complexity ?? "-")}</div>
                  <div className="text-sm text-slate-300">Readiness: {String(delivery.tcs_implementation_readiness ?? "-")}</div>
                  <div className="text-sm text-slate-300">Training: {String(delivery.training_effort_required ?? "-")}</div>
                  <div className="text-sm text-slate-300">Support: {String(delivery.support_scalability ?? "-")}</div>
                  <div className="mt-2 text-sm text-slate-400">Integration Requirements</div>
                  <div className="mt-1 text-sm">{integrationReqs.length ? integrationReqs.join(", ") : "-"}</div>
                </div>
              )}
            </div>

            <div className="max-h-64 overflow-auto rounded-xl border border-white/10 bg-black/20 p-4">
              <div className="sticky top-0 z-10 -mx-4 mb-2 flex items-center justify-between gap-2 border-b border-white/10 bg-slate-900 px-4 py-2">
                <div className="text-sm uppercase tracking-wide text-slate-400">Commercial Viability</div>
                <button
                  type="button"
                  onClick={() => toggleInsightBlock("commercial_viability")}
                  className="rounded-md border border-white/20 px-2 py-1 text-xs font-semibold text-slate-200 hover:bg-white/10"
                >
                  {expandedInsightBlocks.commercial_viability ? "Hide" : "Detail"}
                </button>
              </div>
              {expandedInsightBlocks.commercial_viability && (
                <div className="pt-1">
                  <div className="mt-2 text-sm text-slate-300">Model: {String(commercial.monetization_model ?? "-")}</div>
                  <div className="text-sm text-slate-300">GTM: {String(commercial.gtm_model ?? "-")}</div>
                  <div className="text-sm text-slate-300">Pricing Transparent: {yesNo(commercial.pricing_transparency)}</div>
                  <div className="text-sm text-slate-300">Partner Willingness: {yesNo(commercial.partner_willingness)}</div>
                  <div className="text-sm text-slate-300">Est. Deal Size: {String(commercial.estimated_deal_size_usd ?? "-")}</div>
                </div>
              )}
            </div>
          </div>
          {!result && <div className="mt-4 text-sm text-slate-400">Run an analysis to populate the key insight blocks.</div>}
        </div>
      </section>


{/* feature highlight section */}
      <section className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-3">
        {[{ icon: ShieldCheck, title: "Strict JSON Schema" }, { icon: Brain, title: "Two-Agent Analysis" }, { icon: Sparkles, title: "Download-Ready JSON" }].map((item) => (
          <div key={item.title} className="glass rounded-2xl p-4 text-sm">
            <item.icon className="mb-2 h-5 w-5 text-mint" />
            {item.title}
          </div>
        ))}
      </section>
      </div>
    </>
  );
}
