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
      <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-2xl font-extrabold tracking-tight text-white">Strategy Baseline Performance</h1>
          <p className="text-xs text-slate-400">
            Three-way strategy comparison on held-out test split (single run). For multi-seed paired treatment effects, sensitivity sweeps, and operating boundary analysis across 710 invoices, see <code className="text-slate-300">docs/EVALUATION_METHODOLOGY.md</code>.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {recoveryLift !== null && (
            <span
              className={`rounded-xl border px-3 py-1.5 text-xs font-bold ${
                recoveryLift > 0
                  ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-400"
                  : recoveryLift < 0
                  ? "border-rose-500/30 bg-rose-500/10 text-rose-400"
                  : "border-slate-700 bg-slate-800/50 text-slate-300"
              }`}
            >
              {recoveryLift > 0 ? `+${recoveryLift.toFixed(1)}pp` : `${recoveryLift.toFixed(1)}pp`} Recovery vs No-Agent (single split)
            </span>
          )}
          {contactReductionPct !== null && (
            <span
              className={`rounded-xl border px-3 py-1.5 text-xs font-bold ${
                contactReductionPct > 0
                  ? "border-sky-500/30 bg-sky-500/10 text-sky-400"
                  : "border-slate-700 bg-slate-800/50 text-slate-300"
              }`}
            >
              {contactReductionPct > 0
                ? `-${contactReductionPct.toFixed(1)}%`
                : `+${Math.abs(contactReductionPct).toFixed(1)}%`}{" "}
              Messages (single split)
            </span>
          )}
        </div>
      </div>

      <BaselineComparison rows={payload.data} />
    </div>
  );
}
