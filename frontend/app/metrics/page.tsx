import { BaselineComparison } from "../../components/dashboard/BaselineComparison";
import { listBaselines } from "../../lib/api";

export async function MetricsPage() {
  const payload = await listBaselines();
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Recovery vs baselines</h1>
      <p className="text-sm text-slate-400">
        Three-way comparison on the generator held-out split: no agent, naive 7-day cadence, DueBot.
      </p>
      <BaselineComparison rows={payload.data} />
    </div>
  );
}

export default MetricsPage;
