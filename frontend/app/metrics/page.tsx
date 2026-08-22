import { BaselineComparison } from "../../components/dashboard/BaselineComparison";
import { listBaselines } from "../../lib/api";

export default async function MetricsPage() {
  const payload = await listBaselines();

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-2xl font-extrabold tracking-tight text-white">Strategy Baseline Performance</h1>
          <p className="text-xs text-slate-400">
            Three-way strategy comparison on held-out synthetic test dataset: No Agent vs Naive 7-Day Cadence vs DueBot.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="rounded-xl border border-sky-500/30 bg-sky-500/10 px-3 py-1.5 text-xs font-bold text-sky-400">
            +93.9% Capital Efficiency
          </span>
        </div>
      </div>

      <BaselineComparison rows={payload.data} />
    </div>
  );
}
