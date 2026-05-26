import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ShieldCheck } from "lucide-react";

import { FixedHeader } from "../components/FixedHeader";
import { getDecisionIntelligenceReport, listStoredJsons, type DecisionIntelligenceReport, type StoredJsonItem } from "../lib/api";

function isPass(value: boolean) {
  return value ? "text-mint" : "text-rose-300";
}

function isYes(value: "YES" | "NO") {
  return value === "YES";
}

export default function DecisionIntelligencePage() {
  const [items, setItems] = useState<StoredJsonItem[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [submittedId, setSubmittedId] = useState("");
  const [report, setReport] = useState<DecisionIntelligenceReport | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const load = async () => {
      const files = await listStoredJsons();
      setItems(files);
    };
    void load();
  }, []);

  const submitSelection = async () => {
    if (!selectedId) return;
    setLoading(true);
    setReport(null);
    setSubmittedId("");
    try {
      const res = await getDecisionIntelligenceReport(selectedId);
      setReport(res);
      setSubmittedId(selectedId);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <FixedHeader />
      <div className="mx-auto max-w-7xl px-4 pb-8 pt-24 md:px-8">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-3xl font-bold md:text-5xl">Decision Intelligence</h1>
        <Link to="/" className="rounded-lg border border-white/20 px-4 py-2 text-sm hover:bg-white/10">
          Home
        </Link>
      </div>

      <div className="glass mb-6 rounded-2xl p-5">
        <div className="mb-2 text-sm text-cyan">Choose Recently Analyzed Company JSON</div>
        <div className="flex flex-col gap-3 md:flex-row">
          <select
            value={selectedId}
            onChange={(e) => setSelectedId(e.target.value)}
            className="w-full rounded-xl border border-white/20 bg-slate-100 px-4 py-3 text-slate-900"
          >
            <option value="" disabled>
              {items.length === 0 ? "No stored files found" : "Select a JSON file from storage"}
            </option>
            {items.map((item) => (
              <option key={item.id} value={item.id}>
                {item.filename}
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
        {!submittedId && <div className="mt-3 text-xs text-slate-400">Pick a file from storage and click Submit to generate the report.</div>}
      </div>

      {report ? (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <div className="glass rounded-2xl p-5">
            <div className="mb-3 flex items-center gap-2 text-sm text-cyan">
              <ShieldCheck className="h-4 w-4" /> Gate 1 - Enterprise Credibility
            </div>
            <div className={`mb-4 text-lg font-semibold ${isPass(report.gate_1.status === "PASS")}`}>
              {report.gate_1.status}
            </div>
            <div className="space-y-2 text-sm">
              {Object.entries(report.gate_1.criteria).map(([key, criterion]) => (
                <div key={key} className="rounded-lg border border-white/10 bg-black/20 p-3">
                  <div className="flex items-center justify-between gap-3">
                    <span>{key.replaceAll("_", " ")}</span>
                    <span className={isPass(isYes(criterion.decision))}>{criterion.decision}</span>
                  </div>
                  <div className="mt-2 text-xs text-slate-300">{criterion.reason || "No reason provided."}</div>
                </div>
              ))}
            </div>
          </div>

          <div className="glass rounded-2xl p-5">
            <div className="mb-3 flex items-center gap-2 text-sm text-cyan">
              <ShieldCheck className="h-4 w-4" /> Gate 2 - Strategic Relevance
            </div>
            <div className={`mb-4 text-lg font-semibold ${isPass(report.gate_2.status === "PASS")}`}>
              {report.gate_2.status}
            </div>
            <div className="space-y-2 text-sm">
              {Object.entries(report.gate_2.criteria).map(([key, criterion]) => (
                <div key={key} className="rounded-lg border border-white/10 bg-black/20 p-3">
                  <div className="flex items-center justify-between gap-3">
                    <span>{key.replaceAll("_", " ")}</span>
                    <span className={isPass(isYes(criterion.decision))}>{criterion.decision}</span>
                  </div>
                  <div className="mt-2 text-xs text-slate-300">{criterion.reason || "No reason provided."}</div>
                </div>
              ))}
            </div>
          </div>
          <div className="glass rounded-2xl p-5 lg:col-span-2">
            <div className="mb-2 text-sm text-cyan">Overall Partnership Recommendation</div>
            <div className="text-lg font-semibold text-white">{report.overall_partnership_recommendation.priority}</div>
            <div className="mt-2 text-sm text-slate-300">{report.overall_partnership_recommendation.reason}</div>
          </div>
        </div>
      ) : (
        !loading 
      )}
      </div>
    </>
  );
}
