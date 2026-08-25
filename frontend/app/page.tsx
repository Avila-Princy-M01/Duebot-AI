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
      <div className="glass-panel relative overflow-hidden rounded-3xl p-8 sm:p-10 shadow-2xl">
        <div className="absolute -top-24 -right-24 h-80 w-80 rounded-full bg-gradient-to-br from-sky-500/20 via-blue-600/15 to-indigo-600/10 blur-3xl pointer-events-none" />
        <div className="absolute -bottom-24 -left-24 h-80 w-80 rounded-full bg-gradient-to-tr from-emerald-500/15 via-teal-500/10 to-transparent blur-3xl pointer-events-none" />

        <div className="relative z-10 flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
          <div className="max-w-3xl space-y-3">
            <div className="inline-flex items-center gap-2 rounded-full border border-sky-400/30 bg-sky-500/10 px-3.5 py-1 text-xs font-extrabold text-sky-300 shadow-sm shadow-sky-500/10">
              <span className="flex h-2 w-2 rounded-full bg-sky-400 animate-pulse" />
              <span>Razorpay AI Collections Agent</span>
            </div>
            <h1 className="text-3xl font-extrabold tracking-tight text-white sm:text-4xl md:text-5xl">
              Autonomous Receivables Recovery with Deterministic Safety
            </h1>
            <p className="text-sm font-medium text-slate-300 leading-relaxed max-w-2xl">
              DueBot automates contextual B2B collections over WhatsApp, tracks promises, and safety-routes uncertain buyer replies to Human Review. The LLM suggests; the state machine enforces.
            </p>
          </div>

          <div className="flex-shrink-0">
            <SeedButton />
          </div>
        </div>
      </div>

      {error ? (
        <div className="rounded-2xl border border-amber-500/40 bg-amber-950/30 p-5 text-xs text-amber-200 backdrop-blur-md" role="alert">
          <p className="font-bold">{error}</p>
          <p className="mt-1 text-slate-400">
            Start the API backend (`uvicorn backend.main:app`), then click Seed Synthetic Batch.
          </p>
        </div>
      ) : null}

      {/* Metric Cards Grid */}
      <div className="grid gap-5 md:grid-cols-3">
        <MetricCard
          label="Invoices Loaded"
          value={String(invoices.length)}
          type="loaded"
          hint="Total receivables in portfolio"
        />
        <MetricCard
          label="Overdue / Active Queue"
          value={String(overdue.length)}
          type="overdue"
          hint="Active collection workload"
        />
        <MetricCard
          label="₹ Amount At Risk"
          value={`₹${atRisk.toLocaleString("en-IN", { maximumFractionDigits: 0 })}`}
          type="risk"
          hint="Total overdue receivables balance"
        />
      </div>

      {/* Aging Distribution */}
      <AgingBuckets invoices={invoices} />

      {/* Quick Summary Architecture Grid */}
      <div className="grid gap-6 md:grid-cols-2">
        <div className="glass-card rounded-3xl p-6 transition-all hover:border-emerald-500/30">
          <div className="flex items-center gap-3 mb-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-emerald-500/15 border border-emerald-400/30 text-emerald-400 shadow-sm">
              🛡️
            </div>
            <h3 className="text-sm font-bold text-white">Deterministic Policy Guardrails</h3>
          </div>
          <p className="text-xs text-slate-300 leading-relaxed">
            The state machine strictly enforces max 3 contacts per week, respects opted-out buyers, and halts automated nudges immediately when a payment promise or dispute is detected.
          </p>
        </div>

        <div className="glass-card rounded-3xl p-6 transition-all hover:border-sky-500/30">
          <div className="flex items-center gap-3 mb-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-sky-500/15 border border-sky-400/30 text-sky-400 shadow-sm">
              ⚡
            </div>
            <h3 className="text-sm font-bold text-white">Frictionless Razorpay Payment Links</h3>
          </div>
          <p className="text-xs text-slate-300 leading-relaxed">
            Nudges embed instant Razorpay payment links directly into WhatsApp messages, accelerating self-cure rates while preserving buyer relationship trust.
          </p>
        </div>
      </div>
    </div>
  );
}
