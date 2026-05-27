import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ShieldCheck } from "lucide-react";
import toast, { Toaster } from "react-hot-toast";

import { FixedHeader } from "../components/FixedHeader";
import {
  getCompanyProfile,
  getDecisionIntelligenceReport,
  listCompanyProfiles,
  type CompanyProfileDetail,
  type CompanyProfileSummary,
  type DecisionIntelligenceReport,
} from "../lib/api";

function isPass(value: boolean) {
  return value ? "text-mint" : "text-rose-300";
}

function isYes(value: "YES" | "NO") {
  return value === "YES";
}

function labelize(value: string) {
  return value.replace(/_/g, " ");
}

function getDeterminismLabel(gate: "G1" | "G2", index: number) {
  if (gate === "G1" && index < 3) return "DETERMINISTIC";
  return "NON-DETERMINISTIC";
}

export default function DecisionIntelligencePage() {
  const [items, setItems] = useState<CompanyProfileSummary[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [profile, setProfile] = useState<CompanyProfileDetail | null>(null);
  const [report, setReport] = useState<DecisionIntelligenceReport | null>(null);
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
    setProfile(null);
    setReport(null);
    try {
      const [selectedProfile, gateReport] = await Promise.all([
        getCompanyProfile(Number(selectedId)),
        getDecisionIntelligenceReport(selectedId),
      ]);
      setProfile(selectedProfile);
      setReport(gateReport);
      toast.success("Decision intelligence generated");
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || "Failed to generate decision intelligence");
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <FixedHeader />
      <div className="mx-auto max-w-7xl px-4 pb-8 pt-24 md:px-8">
        <Toaster position="top-right" />
        <div className="mb-6 flex items-center justify-between">
          <h1 className="text-3xl font-bold md:text-5xl">Decision Intelligence</h1>
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
          {profile && (
            <div className="mt-3 text-xs text-slate-400">
              Selected: {profile.company_name || `Profile ${profile.id}`} | Generated {new Date(profile.created_at).toLocaleString()}
            </div>
          )}
          {/* {!report && (
            <div className="mt-3 text-sm text-slate-400">
              Select a company profile and submit to generate Gate 1 and Gate 2 intelligence.
            </div>
          )} */}
        </div>

        {report ? (
          <div>
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
              <div className="glass rounded-2xl p-5">
                <div className="mb-3 flex items-center gap-2 text-sm font-bold uppercase text-cyan">
                  <ShieldCheck className="h-4 w-4" /> Gate 1 - Enterprise Credibility
                </div>
                <div className={`mb-4 text-lg font-semibold ${isPass(report.gate_1.status === "PASS")}`}>
                  {report.gate_1.status}
                </div>
                <div className="space-y-2 text-sm">
                  {Object.entries(report.gate_1.criteria).map(([key, criterion], index) => (
                    <div key={key} className="rounded-lg border border-white/10 bg-black/20 p-3">
                      <div className="flex items-center justify-between gap-3">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="font-bold uppercase">{`G1.${index + 1} ${labelize(key)}`}</span>
                          <span className="rounded-full border border-cyan/40 bg-cyan/10 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-cyan">
                            {getDeterminismLabel("G1", index)}
                          </span>
                        </div>
                        <span className={isPass(isYes(criterion.decision))}>{criterion.decision}</span>
                      </div>
                      <div className="mt-2 text-xs text-slate-300">{criterion.reason || "No reason provided."}</div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="glass rounded-2xl p-5">
                <div className="mb-3 flex items-center gap-2 text-sm font-bold uppercase text-cyan">
                  <ShieldCheck className="h-4 w-4" /> Gate 2 - Strategic Relevance
                </div>
                <div className={`mb-4 text-lg font-semibold ${isPass(report.gate_2.status === "PASS")}`}>
                  {report.gate_2.status}
                </div>
                <div className="space-y-2 text-sm">
                  {Object.entries(report.gate_2.criteria).map(([key, criterion], index) => (
                    <div key={key} className="rounded-lg border border-white/10 bg-black/20 p-3">
                      <div className="flex items-center justify-between gap-3">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="font-bold uppercase">{`G2.${index + 1} ${labelize(key)}`}</span>
                          <span className="rounded-full border border-cyan/40 bg-cyan/10 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-cyan">
                            {getDeterminismLabel("G2", index)}
                          </span>
                        </div>
                        <span className={isPass(isYes(criterion.decision))}>{criterion.decision}</span>
                      </div>
                      <div className="mt-2 text-xs text-slate-300">{criterion.reason || "No reason provided."}</div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* <div className="glass mt-6 w-full rounded-2xl p-5">
              <div className="mb-2 text-sm text-cyan">Overall Partnership Recommendation</div>
              <div className="text-lg font-semibold text-white">{report.overall_partnership_recommendation.priority}</div>
              <div className="mt-2 text-sm text-slate-300">{report.overall_partnership_recommendation.reason}</div>
            </div> */}
          </div>
        ) : (
          <></>
        )}
      </div>
    </>
  );
}
