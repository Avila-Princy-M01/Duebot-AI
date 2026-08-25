import { BaselineComparison } from "../../components/dashboard/BaselineComparison";
import { listBaselines } from "../../lib/api";

export default async function MetricsPage() {
  const payload = await listBaselines();
  const duebotRow = payload.data.find((r) => r.strategy.toLowerCase().includes("duebot"));
  const naiveRow = payload.data.find((r) => r.strategy.toLowerCase().includes("naive"));
  const noAgentRow = payload.data.find(
    (r) => r.strategy.toLowerCase().includes("no_agent") || r.strategy.toLowerCase().includes("none")
  );

  const contactReductionPct =
    duebotRow && naiveRow && naiveRow.total_contacts_sent > 0
      ? ((1 - duebotRow.total_contacts_sent / naiveRow.total_contacts_sent) * 100).toFixed(1)
      : null;

  const duebotRate =
    duebotRow && parseFloat(duebotRow.total_value) > 0
      ? (parseFloat(duebotRow.recovered_value) / parseFloat(duebotRow.total_value)) * 100
      : null;

  const noAgentRate =
    noAgentRow && parseFloat(noAgentRow.total_value) > 0
      ? (parseFloat(noAgentRow.recovered_value) / parseFloat(noAgentRow.total_value)) * 100
      : null;

  const recoveryLift =
    duebotRate !== null && noAgentRate !== null ? (duebotRate - noAgentRate).toFixed(1) : null;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-2xl font-extrabold tracking-tight text-white">Strategy Baseline Performance</h1>
          <p className="text-xs text-slate-400">
            Three-way strategy comparison on held-out test split (live run). For full 10-seed paired treatment effects across 710 invoices (61.5% fewer messages, +4.9% recovery, 0 dispute spam), see <code className="text-slate-300">docs/EVALUATION_METHODOLOGY.md</code>.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {recoveryLift !== null && parseFloat(recoveryLift) > 0 && (
            <span className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-3 py-1.5 text-xs font-bold text-emerald-400">
              +{recoveryLift}% Recovery vs No-Agent (live split)
            </span>
          )}
          {contactReductionPct !== null && (
            <span className="rounded-xl border border-sky-500/30 bg-sky-500/10 px-3 py-1.5 text-xs font-bold text-sky-400">
              -{contactReductionPct}% Messages (live split)
            </span>
          )}
        </div>
      </div>

      <BaselineComparison rows={payload.data} />
    </div>
  );
}
