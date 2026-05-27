import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import toast, { Toaster } from "react-hot-toast";

import { FixedHeader } from "../components/FixedHeader";
import { getScoringReport, listCompanyProfiles, type CompanyProfileSummary, type ScoringReport } from "../lib/api";

function labelize(value: string) {
  return value.replace(/_/g, " ");
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
        <div className="glass mb-6 rounded-3xl p-8 md:p-12">
          <div className="mb-4 flex items-center justify-between gap-4">
            <h1 className="text-3xl font-bold md:text-5xl">Scoring</h1>
            <Link to="/" className="rounded-lg border border-white/20 px-4 py-2 text-sm hover:bg-white/10">
              Home
            </Link>
          </div>
          <p className="text-slate-300">Evaluate weighted scores across 3 pillars.</p>
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

        {report && (
          <div className="space-y-6">
            <div className="glass rounded-2xl p-5">
              <div className="text-sm text-cyan">Overall</div>
              <div className="mt-2 text-xl font-semibold text-white">Total Weighted Score: {report.total_weighted_score}</div>
              <div className="mt-2 text-sm text-slate-300">{report.overall_summary || "No summary provided."}</div>
            </div>

            <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
              {pillars.map((pillar) => (
                <div key={pillar.code} className="glass rounded-2xl p-5">
                  <div className="text-sm font-bold uppercase text-cyan">{pillar.code} - {pillar.title}</div>
                  <div className="mt-2 text-sm text-slate-300">Weight: {pillar.data.weight}</div>
                  <div className="text-sm text-slate-300">Raw Score: {pillar.data.raw_score} / 5</div>
                  <div className="text-sm text-slate-300">Weighted Score: {pillar.data.weighted_score}</div>
                  <div className="mt-2 text-xs text-slate-300">{pillar.data.summary || "No summary provided."}</div>
                  <div className="mt-3 space-y-2 text-sm">
                    {Object.entries(pillar.data.sub_criteria).map(([key, sub]) => (
                      <div key={key} className="rounded-lg border border-white/10 bg-black/20 p-3">
                        <div className="flex items-center justify-between gap-2">
                          <span className="font-semibold uppercase">{labelize(key)}</span>
                          <span className="text-cyan">{sub.score}</span>
                        </div>
                        <div className="mt-1 text-xs text-slate-300">{sub.reason || "No reason provided."}</div>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
        {!report && (
          <div className="text-sm text-slate-400">Select a company profile and submit to generate scoring.</div>
        )}
        </div>
    </>
  );
}
