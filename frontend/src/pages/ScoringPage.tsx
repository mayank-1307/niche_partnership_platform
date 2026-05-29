import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ShieldCheck } from "lucide-react";
import toast, { Toaster } from "react-hot-toast";

import { FixedHeader } from "../components/FixedHeader";
import { getScoringReport, listCompanyProfiles, type CompanyProfileSummary, type ScoringReport } from "../lib/api";

function labelize(value: string) {
  return value.replace(/_/g, " ");
}

function scoreClass(score: number) {
  if (score >= 4) return "text-mint";
  if (score >= 3) return "text-amber-300";
  return "text-rose-300";
}

export default function ScoringPage() {
  const [items, setItems] = useState<CompanyProfileSummary[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [report, setReport] = useState<ScoringReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadingProfiles, setLoadingProfiles] = useState(false);

  useEffect(() => {
    const loadProfiles = async () => {
      setLoadingProfiles(true);
      try {
        const profiles = await listCompanyProfiles();
        setItems(profiles);
      } catch (error: any) {
        toast.error(error?.response?.data?.detail || "Failed to load company profiles");
      } finally {
        setLoadingProfiles(false);
      }
    };
    void loadProfiles();
  }, []);

  const submitSelection = async () => {
    if (!selectedId) return;
    setLoading(true);
    setReport(null);
    try {
      const scoringReport = await getScoringReport(selectedId);
      setReport(scoringReport);
      toast.success("Scoring generated");
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || "Failed to generate scoring");
    } finally {
      setLoading(false);
    }
  };

  const pillars = report
    ? [
        { code: "P1", title: "Domain & Solution Depth", data: report.pillars.p1_domain_solution_depth },
        { code: "P2", title: "Product & Engineering Readiness", data: report.pillars.p2_product_engineering_readiness },
        { code: "P3", title: "AI Transparency & Trustworthiness", data: report.pillars.p3_ai_transparency_trustworthiness },
      ]
    : [];

  return (
    <>
      <FixedHeader />
      <div className="mx-auto max-w-7xl px-4 pb-8 pt-24 md:px-8">
        <Toaster position="top-right" />
        <div className="mb-6 flex items-center justify-between">
          <h1 className="text-3xl font-bold md:text-5xl">Scoring</h1>
          <Link to="/" className="rounded-lg border border-white/20 px-4 py-2 text-sm hover:bg-white/10">
            Home
          </Link>
        </div>

        <div className="glass mb-6 rounded-2xl p-5">
          <div className="mb-2 text-sm text-cyan">Choose Company Profile</div>
          <div className="flex flex-col gap-3 md:flex-row">
            <select
              value={selectedId}
              onChange={(e) => setSelectedId(e.target.value)}
              className="w-full rounded-xl border border-white/20 bg-slate-100 px-4 py-3 text-slate-900"
            >
              <option value="" disabled>
                {items.length === 0 ? (loadingProfiles ? "Loading profiles..." : "No profiles found") : "Choose recently analyzed partner company json for scoring"}
              </option>
              {items.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.company_name || `Profile ${item.id}`} ({new Date(item.created_at).toLocaleString()})
                </option>
              ))}
            </select>
            <button
              type="button"
              onClick={() => void submitSelection()}
              disabled={!selectedId || loading}
              className="rounded-xl bg-gradient-to-r from-cyan to-indigo px-6 py-3 font-semibold text-black disabled:opacity-60"
            >
              {loading ? "Generating..." : "Submit"}
            </button>
          </div>
        </div>

        {report ? (
          <div>
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
              {pillars.map((pillar) => (
                <div key={pillar.code} className="glass rounded-2xl p-5">
                  <div className="mb-3 flex items-center gap-2 text-sm font-bold uppercase text-cyan">
                    <ShieldCheck className="h-4 w-4" /> {pillar.code} - {pillar.title}
                  </div>
                  <div className={`mb-4 text-lg font-semibold ${scoreClass(pillar.data.raw_score)}`}>
                    {pillar.data.raw_score} / 5
                  </div>
                  <div className="mb-3 flex flex-wrap gap-2 text-xs text-slate-300">
                    <span className="rounded-full border border-cyan/40 bg-cyan/10 px-2 py-0.5 font-bold uppercase tracking-wide text-cyan">
                      Weight {pillar.data.weight}
                    </span>
                    <span className="rounded-full border border-cyan/40 bg-cyan/10 px-2 py-0.5 font-bold uppercase tracking-wide text-cyan">
                      Weighted {pillar.data.weighted_score}
                    </span>
                  </div>
                  <div className="mb-3 text-xs text-slate-300">{pillar.data.summary || "No summary provided."}</div>
                  <div className="mt-3 space-y-2 text-sm">
                    {Object.entries(pillar.data.sub_criteria).map(([key, sub]) => (
                      <div key={key} className="rounded-lg border border-white/10 bg-black/20 p-3">
                        <div className="flex items-center justify-between gap-3">
                          <span className="font-bold uppercase">{labelize(key)}</span>
                          <span className={scoreClass(sub.score)}>{sub.score}</span>
                        </div>
                        <div className="mt-2 text-xs text-slate-300">{sub.reason || "No reason provided."}</div>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>

            <div className="glass mt-6 w-full rounded-2xl p-5">
              <div className="mb-2 text-sm text-cyan">Scoring Summary</div>
              <div className="space-y-1 text-sm text-slate-200">
                <div>
                  Total Weighted Score: <span className={scoreClass(report.total_weighted_score)}>{report.total_weighted_score}</span>
                </div>
                {pillars.map((pillar) => (
                  <div key={pillar.code}>
                    {pillar.code}: <span className={scoreClass(pillar.data.raw_score)}>{pillar.data.raw_score} / 5</span>
                  </div>
                ))}
              </div>
              <div className="mt-4 text-sm text-slate-300">{report.overall_summary || "No summary provided."}</div>
            </div>
          </div>
        ) : (
          <div className="text-sm text-slate-400"></div>
        )}
      </div>
    </>
  );
}
