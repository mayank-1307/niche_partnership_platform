import { motion } from "framer-motion";
import { Brain, ChevronDown, ChevronUp, ShieldCheck, Sparkles } from "lucide-react";
import { useEffect, useRef, useState, type ChangeEvent } from "react";
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
import { formatCurrencyDisplay, formatUsd } from "./lib/format";

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

function renderSourceList(sources: string[]) {
  if (sources.length === 0) {
    return <div className="mt-3 text-xs text-slate-500">No section-specific sources were identified.</div>;
  }

  return (
    <div className="mt-3">
      <div className="text-xs uppercase tracking-wide text-slate-400">Relevant Sources</div>
      <div className="mt-2 space-y-2">
        {sources.map((source, index) => {
          const isUrl = /^https?:\/\//i.test(source);

          return (
            <div key={`${source}-${index}`} className="rounded-lg border border-white/10 bg-black/25 p-2 text-xs text-slate-200">
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
    </div>
  );
}

function InsightToggle({ expanded, onClick, label }: { expanded: boolean; onClick: () => void; label: string }) {
  const Icon = expanded ? ChevronUp : ChevronDown;
  const action = expanded ? "Collapse" : "Expand";

  return (
    <button
      type="button"
      onClick={onClick}
      aria-expanded={expanded}
      aria-label={`${action} ${label} details`}
      title={`${action} details`}
      className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-md border border-white/20 text-slate-200 transition hover:bg-white/10"
    >
      <Icon className="h-4 w-4" />
    </button>
  );
}

export default function App() {
  const [domain, setDomain] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AnalyzeResponse | null>(null);
  const [inputLocked, setInputLocked] = useState(false);
  const [sourceDocument, setSourceDocument] = useState<File | null>(null);
  const [expandedInsightBlocks, setExpandedInsightBlocks] = useState<Record<string, boolean>>({});
  const [recentProfiles, setRecentProfiles] = useState<CompanyProfileSummary[]>([]);
  const [loadingRecentProfiles, setLoadingRecentProfiles] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    if (inputLocked) {
      return;
    }

    const query = domain.trim();
    let active = true;
    const timer = window.setTimeout(async () => {
      if (!active) {
        return;
      }
      setLoadingRecentProfiles(true);
      try {
        const items = await listCompanyProfiles(query);
        if (!active) {
          return;
        }
        setRecentProfiles(items.slice(0, 5));
      } catch (error: any) {
        if (!active) {
          return;
        }
        toast.error(error?.response?.data?.detail || "Failed to load recent searches");
      } finally {
        if (!active) {
          return;
        }
        setLoadingRecentProfiles(false);
      }
    }, 300);

    return () => {
      active = false;
      window.clearTimeout(timer);
    };
  }, [domain, inputLocked]);

  const run = async () => {
    if (!domain.trim()) {
      toast.error("Enter a company domain");
      return;
    }

    setInputLocked(true);
    setLoading(true);
    setResult(null);
    try {
      const res = await analyzeCompany(domain, sourceDocument);
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

  const openDocumentPicker = () => {
    fileInputRef.current?.click();
  };

  const handleDocumentChange = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0] ?? null;
    setSourceDocument(file);
  };

  const clearDocument = () => {
    setSourceDocument(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
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
  const enterpriseSources = asStringList(enterprise.sources);
  const strategicSources = asStringList(strategic.sources);
  const deliverySources = asStringList(delivery.sources);
  const commercialSources = asStringList(commercial.sources);
  const useCases = asStringList(strategic.primary_use_cases);
  const integrationReqs = asStringList(delivery.integration_requirements);
  const investors = asStringList(funding.investors);
  const rounds = asStringList(funding.recent_rounds);
  const leaders = asStringList(leadership.key_leaders);
  const companyName = typeof structured.company_name === "string" ? structured.company_name.trim() : "";
  const hasCompanyName = Boolean(result && companyName);

  return (
    <>
      <FixedHeader pageTitle="Partner Analysis" />
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
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center">
          <div className="w-full">
            <input
              value={domain}
              onChange={(e) => setDomain(e.target.value)}
              placeholder="Please enter the company domain (e.g., https://company.com)"
              disabled={inputLocked}
              className="w-full rounded-xl border border-white/10 bg-black/30 px-4 py-3 outline-none focus:border-cyan/50"
            />
            <p className="mt-2 text-xs text-slate-400">
              **The agents are accessing data from the official sites as well as publicly available sources**
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
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
            <button
              type="button"
              onClick={openDocumentPicker}
              disabled={loading || inputLocked}
              className="rounded-xl border border-cyan/40 bg-cyan/10 px-6 py-3 font-semibold text-cyan transition hover:bg-cyan/20 disabled:opacity-60"
            >
              {sourceDocument ? "Change Source File" : "Upload Source File"}
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.docx,.txt,.md,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain"
              onChange={handleDocumentChange}
              className="hidden"
              aria-label="Upload company source document"
            />
          </div>
        </div>
        <div className="mt-3 flex flex-wrap items-center gap-3 text-xs text-slate-400">
          <span>Optional company PDF, DOCX, or text source for grounded analysis.</span>
          {sourceDocument && (
            <div className="flex items-center gap-2 rounded-full border border-white/10 bg-black/25 px-3 py-1 text-slate-200">
              <span className="max-w-[16rem] truncate">{sourceDocument.name}</span>
              <button
                type="button"
                onClick={clearDocument}
                disabled={loading || inputLocked}
                className="font-semibold text-cyan hover:text-white disabled:opacity-60"
              >
                Remove
              </button>
            </div>
          )}
        </div>
        <div className="mt-4">
          <div className="mb-2 text-sm text-cyan">{domain.trim() ? "Top 5 Matching Searches" : "Recent 5 Searches"}</div>
          {loadingRecentProfiles ? (
            <div className="text-xs text-slate-400">Loading recent searches...</div>
          ) : recentProfiles.length === 0 ? (
            <div className="text-xs text-slate-400">{domain.trim() ? "No matching recent searches found." : "No recent searches found."}</div>
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
        <div className="flex flex-col gap-6 lg:h-[31rem] lg:min-h-0">
          <div className="glass flex h-full flex-col rounded-2xl p-5 lg:min-h-0">
            <div className="mb-3 flex items-center gap-2 text-sm text-cyan">
              <span>Company Summary</span>
              {hasCompanyName && <span className="text-2xl font-bold">{companyName}</span>}
            </div>
            <div className="prose prose-invert max-w-none flex-1 overflow-auto whitespace-pre-wrap text-sm text-slate-200 lg:min-h-0">
              {result?.company_summary || "Summary will appear after extraction."}
            </div>
          </div>
        </div>

        <div className="lg:h-[31rem] lg:min-h-0">
          <JsonViewer data={result?.structured_json ?? null} downloadUrl={result ? downloadJsonUrl(result.id) : null} companyName={companyName} />
        </div>
      </div>

      <section className="mt-6 space-y-4">
        <div className="glass rounded-2xl p-5">
          <div className="mb-4 flex items-center gap-2 text-sm text-cyan">
            Key Insights Dashboard
          </div>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-2">
            <div className="max-h-64 overflow-auto rounded-xl border border-white/10 bg-black/20 px-4 pb-4 pt-0">
              <div className="sticky top-0 z-10 -mx-4 mb-2 flex items-center justify-between gap-2 border-b border-white/10 bg-slate-900 px-4 py-2">
                <div className="text-sm uppercase tracking-wide text-slate-400">Enterprise Credibility</div>
                <InsightToggle
                  expanded={Boolean(expandedInsightBlocks.company_funding_key_players)}
                  onClick={() => toggleInsightBlock("company_funding_key_players")}
                  label="enterprise credibility"
                />
              </div>
              {expandedInsightBlocks.company_funding_key_players && (
                <div className="">
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
                  {renderSourceList(enterpriseSources)}
                </div>
              )}
            </div>

            <div className="max-h-64 overflow-auto rounded-xl border border-white/10 bg-black/20 px-4 pb-4 pt-0">
              <div className="sticky top-0 z-10 -mx-4 mb-2 flex items-center justify-between gap-2 border-b border-white/10 bg-slate-900 px-4 py-2">
                <div className="text-sm uppercase tracking-wide text-slate-400">Strategic Relevance</div>
                <InsightToggle
                  expanded={Boolean(expandedInsightBlocks.strategic_relevance)}
                  onClick={() => toggleInsightBlock("strategic_relevance")}
                  label="strategic relevance"
                />
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
                  {renderSourceList(strategicSources)}
                </div>
              )}
            </div>

            <div className="max-h-64 overflow-auto rounded-xl border border-white/10 bg-black/20 px-4 pb-4 pt-0">
              <div className="sticky top-0 z-10 -mx-4 mb-2 flex items-center justify-between gap-2 border-b border-white/10 bg-slate-900 px-4 py-2">
                <div className="text-sm uppercase tracking-wide text-slate-400">Delivery Feasibility</div>
                <InsightToggle
                  expanded={Boolean(expandedInsightBlocks.delivery_feasibility)}
                  onClick={() => toggleInsightBlock("delivery_feasibility")}
                  label="delivery feasibility"
                />
              </div>
              {expandedInsightBlocks.delivery_feasibility && (
                <div className="pt-1">
                  <div className="mt-2 text-sm text-slate-300">Complexity: {String(delivery.implementation_complexity ?? "-")}</div>
                  <div className="text-sm text-slate-300">Readiness: {String(delivery.tcs_implementation_readiness ?? "-")}</div>
                  <div className="text-sm text-slate-300">Training: {String(delivery.training_effort_required ?? "-")}</div>
                  <div className="text-sm text-slate-300">Support: {String(delivery.support_scalability ?? "-")}</div>
                  <div className="mt-2 text-sm text-slate-400">Integration Requirements</div>
                  <div className="mt-1 text-sm">{integrationReqs.length ? integrationReqs.join(", ") : "-"}</div>
                  {renderSourceList(deliverySources)}
                </div>
              )}
            </div>

            <div className="max-h-64 overflow-auto rounded-xl border border-white/10 bg-black/20 px-4 pb-4 pt-0">
              <div className="sticky top-0 z-10 -mx-4 mb-2 flex items-center justify-between gap-2 border-b border-white/10 bg-slate-900 px-4 py-2">
                <div className="text-sm uppercase tracking-wide text-slate-400">Commercial Viability</div>
                <InsightToggle
                  expanded={Boolean(expandedInsightBlocks.commercial_viability)}
                  onClick={() => toggleInsightBlock("commercial_viability")}
                  label="commercial viability"
                />
              </div>
              {expandedInsightBlocks.commercial_viability && (
                <div className="pt-1">
                  <div className="mt-2 text-sm text-slate-300">Model: {String(commercial.monetization_model ?? "-")}</div>
                  <div className="text-sm text-slate-300">GTM: {String(commercial.gtm_model ?? "-")}</div>
                  <div className="text-sm text-slate-300">Pricing Transparent: {yesNo(commercial.pricing_transparency)}</div>
                  <div className="text-sm text-slate-300">Partner Willingness: {yesNo(commercial.partner_willingness)}</div>
                  <div className="text-sm text-slate-300">
                    Estimated Deal Size: {formatCurrencyDisplay(commercial.estimated_deal_size_usd, "estimated_deal_size_usd") ?? "-"}
                  </div>
                  {renderSourceList(commercialSources)}
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
