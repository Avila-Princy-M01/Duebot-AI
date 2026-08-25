import { BaselineComparison } from "../../components/dashboard/BaselineComparison";
import { listBaselines } from "../../lib/api";

export default async function MetricsPage() {
  const payload = await listBaselines();
  const duebotRow = payload.data.find((r) => r.strategy.toLowerCase() === "duebot");
  const naiveRow = payload.data.find((r) => r.strategy.toLowerCase() === "naive_cadence");
  const noAgentRow = payload.data.find((r) => r.strategy.toLowerCase() === "no_agent");

  const contactReductionPct =
    duebotRow && naiveRow && naiveRow.total_contacts_sent > 0
      ? (1 - duebotRow.total_contacts_sent / naiveRow.total_contacts_sent) * 100
      : null;

  const duebotRate =
    duebotRow && duebotRow.eval_set_size > 0
      ? (duebotRow.recovered_count / duebotRow.eval_set_size) * 100
      : null;

  const noAgentRate =
    noAgentRow && noAgentRow.eval_set_size > 0
      ? (noAgentRow.recovered_count / noAgentRow.eval_set_size) * 100
      : null;

  const recoveryLift =
    duebotRate !== null && noAgentRate !== null ? duebotRate - noAgentRate : null;

  return (
    <div className="space-y-6">
      <div className="glass-panel relative overflow-hidden rounded-3xl p-6 sm:p-8 flex flex-col gap-4 md:flex-row md:items-center md:justify-between shadow-xl">
        <div className="max-w-2xl space-y-1.5">
          <div className="inline-flex items-center gap-2 rounded-full border border-sky-400/30 bg-sky-500/10 px-3 py-0.5 text-[11px] font-bold text-sky-300">
            <span>Rigorous Benchmark Evaluation</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white">Strategy Baseline Performance</h1>
          <p className="text-xs text-slate-300 leading-relaxed">
            Three-way strategy comparison on held-out test split (single split). For multi-seed paired treatment effects, sensitivity sweeps, and operating boundary analysis across 710 invoices, see <code className="text-sky-300 font-mono">docs/EVALUATION_METHODOLOGY.md</code>.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2.5">
          {recoveryLift !== null && (
            <span
              className={`rounded-2xl border px-3.5 py-2 text-xs font-extrabold shadow-sm ${
                recoveryLift > 0
                  ? "border-emerald-400/30 bg-emerald-500/15 text-emerald-300 shadow-emerald-500/10"
                  : recoveryLift < 0
                  ? "border-rose-400/30 bg-rose-500/15 text-rose-300 shadow-rose-500/10"
                  : "border-slate-700 bg-slate-800/60 text-slate-300"
              }`}
            >
              {recoveryLift > 0 ? `+${recoveryLift.toFixed(1)}pp` : `${recoveryLift.toFixed(1)}pp`} Recovery vs No-Agent
            </span>
          )}
          {contactReductionPct !== null && (
            <span
              className={`rounded-2xl border px-3.5 py-2 text-xs font-extrabold shadow-sm ${
                contactReductionPct > 0
                  ? "border-sky-400/30 bg-sky-500/15 text-sky-300 shadow-sky-500/10"
                  : "border-slate-700 bg-slate-800/60 text-slate-300"
              }`}
            >
              {contactReductionPct > 0
                ? `-${contactReductionPct.toFixed(1)}%`
                : `+${Math.abs(contactReductionPct).toFixed(1)}%`}{" "}
              Messages vs Naive
            </span>
          )}
        </div>
      </div>

      <BaselineComparison rows={payload.data} />
    </div>
  );
}
