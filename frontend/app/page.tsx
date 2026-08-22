import { AgingBuckets } from "../components/dashboard/AgingBuckets";
import { MetricCard } from "../components/dashboard/MetricCards";
import { SeedButton } from "../components/ui/SeedButton";
import { listInvoices } from "../lib/api";
import type { InvoiceRow } from "../lib/types";

export default async function HomePage() {
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
      {/* Hero Banner */}
      <div className="relative overflow-hidden rounded-3xl border border-slate-800/80 bg-gradient-to-r from-panel via-slate-900 to-panel-light p-8 backdrop-blur-xl shadow-2xl shadow-cyan-950/20">
        <div className="absolute top-0 right-0 h-64 w-64 rounded-full bg-gradient-to-br from-sky-500/10 via-blue-500/10 to-transparent blur-3xl" />

        <div className="relative z-10 flex flex-col gap-6 md:flex-row md:items-center md:justify-between">
          <div className="max-w-2xl space-y-2">
            <div className="inline-flex items-center gap-2 rounded-full border border-sky-500/30 bg-sky-500/10 px-3 py-1 text-xs font-bold text-sky-400">
              <span>🚀 Razorpay Buildathon Submission</span>
            </div>
            <h1 className="text-3xl font-extrabold tracking-tight text-white md:text-4xl">
              Collections Overview & Policy Control
            </h1>
            <p className="text-sm font-medium text-slate-400 leading-relaxed">
              DueBot automates B2B invoice collection nudges over WhatsApp, tracks promises, and safety-routes uncertain buyer replies to Human Review. The LLM never decides whether to execute policy.
            </p>
          </div>

          <div className="flex-shrink-0">
            <SeedButton />
          </div>
        </div>
      </div>

      {error ? (
        <div className="rounded-2xl border border-amber-500/40 bg-amber-950/30 p-4 text-xs text-amber-200">
          <p className="font-bold">{error}</p>
          <p className="mt-1 text-slate-400">
            Start the API backend (`uvicorn backend.main:app`), then click Seed Synthetic Batch.
          </p>
        </div>
      ) : null}

      {/* Metric Cards Grid */}
      <div className="grid gap-4 md:grid-cols-3">
        <MetricCard
          label="Invoices Loaded"
          value={String(invoices.length)}
          type="loaded"
          hint="Total receivables in system"
          trend="100% Validated"
        />
        <MetricCard
          label="Overdue / Open"
          value={String(overdue.length)}
          type="overdue"
          hint="Active collection queue"
        />
        <MetricCard
          label="₹ Amount At Risk"
          value={`₹${atRisk.toLocaleString("en-IN", { maximumFractionDigits: 0 })}`}
          type="risk"
          hint="Total overdue balance"
        />
      </div>

      {/* Aging Distribution */}
      <AgingBuckets invoices={invoices} />

      {/* Quick Summary Grid */}
      <div className="grid gap-6 md:grid-cols-2">
        <div className="rounded-2xl border border-slate-800/80 bg-panel/70 p-6 backdrop-blur-md">
          <div className="flex items-center gap-2 mb-3">
            <div className="h-2 w-2 rounded-full bg-emerald-400" />
            <h3 className="text-sm font-bold text-white">Deterministic Guardrails</h3>
          </div>
          <p className="text-xs text-slate-400 leading-relaxed">
            The state machine strictly enforces max 3 contacts per week, respects opted-out buyers, and stops automated nudges immediately when a payment promise or dispute is detected.
          </p>
        </div>

        <div className="rounded-2xl border border-slate-800/80 bg-panel/70 p-6 backdrop-blur-md">
          <div className="flex items-center gap-2 mb-3">
            <div className="h-2 w-2 rounded-full bg-sky-400" />
            <h3 className="text-sm font-bold text-white">Razorpay Payment Nudges</h3>
          </div>
          <p className="text-xs text-slate-400 leading-relaxed">
            Nudges embed friction-free Razorpay test payment links directly into WhatsApp messages, accelerating self-cure rates while preserving buyer relationship trust.
          </p>
        </div>
      </div>
    </div>
  );
}
