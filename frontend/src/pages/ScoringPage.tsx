import { useEffect, useRef, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import toast, { Toaster } from "react-hot-toast";

import { FixedHeader } from "../components/FixedHeader";
import { getScoringReport, type ScoringReport } from "../lib/api";

function labelize(value: string) {
  return value.replace(/^(p\d+)_(\d+)_/i, "$1.$2 ").replace(/_/g, " ");
}

function scoreClass(score: number) {
  if (score >= 4) return "text-mint";
  if (score >= 3) return "text-amber-300";
  return "text-rose-300";
}

export default function ScoringPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const profileId = typeof location.state?.profileId === "string" ? location.state.profileId : "";
  const [report, setReport] = useState<ScoringReport | null>(null);
  const [loading, setLoading] = useState(false);
  const requestedProfileId = useRef<string | null>(null);

  useEffect(() => {
    if (requestedProfileId.current === profileId) return;
    requestedProfileId.current = profileId;

    const loadScoring = async () => {
      if (!profileId) {
        toast.error("Choose a company profile from Decision Intelligence first");
        navigate("/decision-intelligence", { replace: true });
        return;
      }

      setLoading(true);
      setReport(null);
      try {
        const scoreResponse = await getScoringReport(profileId);
        setReport(scoreResponse.report);
        if (scoreResponse.is_cached) {
          toast("Evaluation is already done.", { icon: "ℹ️" });
        } else {
          toast.success("Scoring generated");
        }
      } catch (error: any) {
        toast.error(error?.response?.data?.detail || "Failed to generate scoring");
      } finally {
        setLoading(false);
      }
    };
    void loadScoring();
  }, [navigate, profileId]);

  const pillars = report
    ? [
        { code: "P1", title: "Domain & Solution Depth", data: report.pillars.p1_domain_solution_depth },
        { code: "P2", title: "Product & Engineering Readiness", data: report.pillars.p2_product_engineering_readiness },
        { code: "P3", title: "AI Transparency & Trustworthiness", data: report.pillars.p3_ai_transparency_trustworthiness },
        { code: "P4", title: "Business & Strategic Fit for TCS", data: report.pillars.p4_business_strategic_fit_for_tcs },
        { code: "P5", title: "Market Validation & Feedback", data: report.pillars.p5_market_validation_feedback },
        { code: "P6", title: "Delivery Readiness & Risk", data: report.pillars.p6_delivery_readiness_risk },
      ]
    : [];
  const totalWeight = pillars.reduce((sum, pillar) => sum + pillar.data.weight, 0);

  return (
    <>
      <FixedHeader pageTitle="Scoring" />
      <div className="mx-auto max-w-7xl px-4 pb-8 pt-24 md:px-8">
        <Toaster position="top-right" />
        <div className="mb-6 flex items-center justify-between">
          <h1 className="text-3xl font-bold md:text-5xl">Scoring</h1>
          <Link to="/" className="rounded-lg border border-white/20 px-4 py-2 text-sm hover:bg-white/10">
            Home
          </Link>
        </div>

        {loading && !report ? (
          <div className="flex min-h-[55vh] items-center justify-center">
            <div className="text-center">
              <div className="text-2xl font-semibold text-white md:text-4xl">Evaluation in Progress</div>
              <div className="mt-3 text-sm text-slate-400">Generating weighted scoring from the selected company profile.</div>
            </div>
          </div>
        ) : report ? (
          <div>
            <div className="grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-3">
              {pillars.map((pillar) => (
                <div key={pillar.code} className="glass rounded-2xl p-5">
                  <div className="mb-3 flex items-center gap-2 text-sm font-bold uppercase text-cyan">
                    {pillar.code} - {pillar.title}
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
                  Total Weighted Score: <span className={scoreClass(report.total_weighted_score)}>{report.total_weighted_score}/{totalWeight}</span>
                </div>
              </div>
              <div className="mt-4 text-sm text-slate-300">{report.overall_summary || "No summary provided."}</div>
            </div>
          </div>
        ) : null}
      </div>
    </>
  );
}
