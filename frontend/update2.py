import re

with open('src/pages/DecisionIntelligencePage.tsx', 'r') as f:
    code = f.read()

# 1. Imports
code = code.replace(
    'import { ShieldCheck } from "lucide-react";',
    'import { ShieldCheck, ChevronDown, ChevronUp } from "lucide-react";'
)

# 2. Toggle component
toggle_code = '''function getDeterminismLabel(gate: "G1" | "G2" | "G3" | "G4" | "G5", index: number) {
  if (gate === "G1" && index < 3) return "DETERMINISTIC";
  return "NON-DETERMINISTIC";
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
}'''
code = code.replace(
    'function getDeterminismLabel(gate: "G1" | "G2" | "G3" | "G4" | "G5", index: number) {\n  if (gate === "G1" && index < 3) return "DETERMINISTIC";\n  return "NON-DETERMINISTIC";\n}',
    toggle_code
)

# 3. State
state_code = '''  const [loadingProfiles, setLoadingProfiles] = useState(false);
  const [expandedBlocks, setExpandedBlocks] = useState<Record<string, boolean>>({});

  const toggleBlock = (key: string) => {
    setExpandedBlocks((prev) => ({ ...prev, [key]: !prev[key] }));
  };'''
code = code.replace(
    '  const [loadingProfiles, setLoadingProfiles] = useState(false);',
    state_code
)

# 4. Gate 1
gate_1_old = '''              <div className="glass rounded-2xl p-5">
                <div className="mb-3 flex items-center gap-2 text-sm font-bold uppercase text-cyan">
                  Gate 1 - Enterprise Credibility
                </div>
                <div className={`mb-4 text-lg font-semibold ${isPass(report.gate_1.status === "PASS")}`}>
                  {report.gate_1.status}
                </div>'''

gate_1_new = '''              <div className="max-h-[32rem] overflow-auto rounded-xl border border-white/10 bg-black/20 px-4 pb-4 pt-0 glass">
                <div className="sticky top-0 z-10 -mx-4 mb-2 flex items-center justify-between gap-2 border-b border-white/10 bg-slate-900 px-4 py-2">
                  <div className="text-sm font-bold uppercase tracking-wide text-cyan">Gate 1 - Enterprise Credibility</div>
                  <InsightToggle expanded={Boolean(expandedBlocks.gate_1)} onClick={() => toggleBlock("gate_1")} label="gate_1" />
                </div>
                {expandedBlocks.gate_1 && (
                  <div className="pt-2">
                <div className={`mb-4 text-lg font-semibold ${isPass(report.gate_1.status === "PASS")}`}>
                  {report.gate_1.status}
                </div>'''
code = code.replace(gate_1_old, gate_1_new)

# Gate 2
gate_2_old = '''              <div className="glass rounded-2xl p-5">
                <div className="mb-3 flex items-center gap-2 text-sm font-bold uppercase text-cyan">
                  Gate 2 - Strategic Relevance
                </div>
                <div className={`mb-4 text-lg font-semibold ${isPass(report.gate_2.status === "PASS")}`}>
                  {report.gate_2.status}
                </div>'''

gate_2_new = '''              <div className="max-h-[32rem] overflow-auto rounded-xl border border-white/10 bg-black/20 px-4 pb-4 pt-0 glass">
                <div className="sticky top-0 z-10 -mx-4 mb-2 flex items-center justify-between gap-2 border-b border-white/10 bg-slate-900 px-4 py-2">
                  <div className="text-sm font-bold uppercase tracking-wide text-cyan">Gate 2 - Strategic Relevance</div>
                  <InsightToggle expanded={Boolean(expandedBlocks.gate_2)} onClick={() => toggleBlock("gate_2")} label="gate_2" />
                </div>
                {expandedBlocks.gate_2 && (
                  <div className="pt-2">
                <div className={`mb-4 text-lg font-semibold ${isPass(report.gate_2.status === "PASS")}`}>
                  {report.gate_2.status}
                </div>'''
code = code.replace(gate_2_old, gate_2_new)

# Gate 3
gate_3_old = '''              <div className="glass rounded-2xl p-5">
                <div className="mb-3 flex items-center gap-2 text-sm font-bold uppercase text-cyan">
                  Gate 3 - Delivery Feasibility
                </div>
                <div
                  className={`mb-4 text-lg font-semibold ${gateStatusClass(report.gate_3.status)}`}
                >
                  {report.gate_3.status}
                </div>'''

gate_3_new = '''              <div className="max-h-[32rem] overflow-auto rounded-xl border border-white/10 bg-black/20 px-4 pb-4 pt-0 glass">
                <div className="sticky top-0 z-10 -mx-4 mb-2 flex items-center justify-between gap-2 border-b border-white/10 bg-slate-900 px-4 py-2">
                  <div className="text-sm font-bold uppercase tracking-wide text-cyan">Gate 3 - Delivery Feasibility</div>
                  <InsightToggle expanded={Boolean(expandedBlocks.gate_3)} onClick={() => toggleBlock("gate_3")} label="gate_3" />
                </div>
                {expandedBlocks.gate_3 && (
                  <div className="pt-2">
                <div
                  className={`mb-4 text-lg font-semibold ${gateStatusClass(report.gate_3.status)}`}
                >
                  {report.gate_3.status}
                </div>'''
code = code.replace(gate_3_old, gate_3_new)

# Gate 4
gate_4_old = '''              <div className="glass rounded-2xl p-5">
                <div className="mb-3 flex items-center gap-2 text-sm font-bold uppercase text-cyan">
                  Gate 4 - Commercial Viability
                </div>
                <div className={`mb-4 text-lg font-semibold ${isPass(report.gate_4.status === "PASS")}`}>
                  {report.gate_4.status}
                </div>'''

gate_4_new = '''              <div className="max-h-[32rem] overflow-auto rounded-xl border border-white/10 bg-black/20 px-4 pb-4 pt-0 glass">
                <div className="sticky top-0 z-10 -mx-4 mb-2 flex items-center justify-between gap-2 border-b border-white/10 bg-slate-900 px-4 py-2">
                  <div className="text-sm font-bold uppercase tracking-wide text-cyan">Gate 4 - Commercial Viability</div>
                  <InsightToggle expanded={Boolean(expandedBlocks.gate_4)} onClick={() => toggleBlock("gate_4")} label="gate_4" />
                </div>
                {expandedBlocks.gate_4 && (
                  <div className="pt-2">
                <div className={`mb-4 text-lg font-semibold ${isPass(report.gate_4.status === "PASS")}`}>
                  {report.gate_4.status}
                </div>'''
code = code.replace(gate_4_old, gate_4_new)

# Gate 5
gate_5_old = '''              <div className="glass rounded-2xl p-5">
                <div className="mb-3 flex items-center gap-2 text-sm font-bold uppercase text-cyan">
                  Gate 5 - Geo & Compliance
                </div>
                <div className={`mb-4 text-lg font-semibold ${gateStatusClass(report.gate_5.status)}`}>
                  {report.gate_5.status}
                </div>'''

gate_5_new = '''              <div className="max-h-[32rem] overflow-auto rounded-xl border border-white/10 bg-black/20 px-4 pb-4 pt-0 glass">
                <div className="sticky top-0 z-10 -mx-4 mb-2 flex items-center justify-between gap-2 border-b border-white/10 bg-slate-900 px-4 py-2">
                  <div className="text-sm font-bold uppercase tracking-wide text-cyan">Gate 5 - Geo & Compliance</div>
                  <InsightToggle expanded={Boolean(expandedBlocks.gate_5)} onClick={() => toggleBlock("gate_5")} label="gate_5" />
                </div>
                {expandedBlocks.gate_5 && (
                  <div className="pt-2">
                <div className={`mb-4 text-lg font-semibold ${gateStatusClass(report.gate_5.status)}`}>
                  {report.gate_5.status}
                </div>'''
code = code.replace(gate_5_old, gate_5_new)

# Now we need to close the `pt-2` div for all 5 gates.
# We replace `                  ))}
#                 </div>
#               </div>`
# with:
# `                  ))}
#                 </div>
#                 </div>
#                 )}
#               </div>`

# Wait! The string `                  ))}\n                </div>\n              </div>` appears 5 times.
close_old = '''                  ))}
                </div>
              </div>'''

close_new = '''                  ))}
                </div>
                </div>
                )}
              </div>'''
code = code.replace(close_old, close_new)

# Finally, Gating Summary
summary_old = '''            <div className="glass mt-6 w-full rounded-2xl p-5">
              <div className="mb-2 text-sm text-cyan">Gating Summary</div>
              <div className="space-y-1 text-base text-slate-200">'''

summary_new = '''            <div className="glass mt-6 w-full max-h-[32rem] overflow-auto rounded-xl border border-white/10 bg-black/20 px-4 pb-4 pt-0">
              <div className="sticky top-0 z-10 -mx-4 mb-2 flex items-center justify-between gap-2 border-b border-white/10 bg-slate-900 px-4 py-2">
                <div className="text-sm font-bold uppercase tracking-wide text-cyan">Gating Summary</div>
                <InsightToggle expanded={Boolean(expandedBlocks.summary)} onClick={() => toggleBlock("summary")} label="summary" />
              </div>
              {expandedBlocks.summary && (
                <div className="pt-2">
              <div className="space-y-1 text-base text-slate-200">'''
code = code.replace(summary_old, summary_new)

# And we close the summary pt-2 div before `<div className="mt-4">`
summary_close_old = '''                <div className="mt-2 text-base text-slate-300">
                  {report.overall_partnership_recommendation.reason || "No summary provided."}
                </div>
              </div>
              <div className="mt-4">
                <button'''

summary_close_new = '''                <div className="mt-2 text-base text-slate-300">
                  {report.overall_partnership_recommendation.reason || "No summary provided."}
                </div>
              </div>
              </div>
              )}
              <div className="mt-4">
                <button'''
code = code.replace(summary_close_old, summary_close_new)

with open('src/pages/DecisionIntelligencePage.tsx', 'w') as f:
    f.write(code)
