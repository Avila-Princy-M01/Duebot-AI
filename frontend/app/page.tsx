import { AgingBuckets } from "../components/dashboard/AgingBuckets";
import { MetricCard } from "../components/dashboard/MetricCards";
import { SeedButton } from "../components/ui/SeedButton";
import { listInvoices } from "../lib/api";
import type { InvoiceRow } from "../lib/types";

export async function HomePage() {
  let invoices: InvoiceRow[] = [];
  let error: string | null = null;
  try {
    invoices = (await listInvoices()).data;
  } catch (exc) {
    error = exc instanceof Error ? exc.message : "API unavailable";
  }
  const overdue = invoices.filter((row) => row.status === "overdue" || row.state === "overdue");
  const atRisk = overdue.reduce((sum, row) => sum + Number(row.total_amount) - Number(row.amount_paid), 0);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-semibold">Collections overview</h1>
        <p className="mt-2 max-w-2xl text-slate-400">
          DueBot chases overdue B2B invoices, tracks promises, and stops when it is not sure. The
          LLM never decides whether to act.
        </p>
      </div>
      {error ? (
        <div className="rounded-xl border border-amber-500/40 bg-amber-950/30 p-4 text-sm">
          <p>{error}</p>
          <p className="mt-2 text-slate-400">
            Start the API, set DATABASE_URL if needed, then seed a batch.
          </p>
        </div>
      ) : null}
      <div className="grid gap-4 md:grid-cols-3">
        <MetricCard label="Invoices loaded" value={String(invoices.length)} />
        <MetricCard label="Overdue / open" value={String(overdue.length)} />
        <MetricCard
          label="₹ at risk"
          value={atRisk.toLocaleString("en-IN", { maximumFractionDigits: 0 })}
        />
      </div>
      <AgingBuckets invoices={invoices} />
      <SeedButton />
    </div>
  );
}

export default HomePage;
