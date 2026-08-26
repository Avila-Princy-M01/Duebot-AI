import Link from "next/link";
import { AgingBuckets } from "../components/dashboard/AgingBuckets";
import { MetricCard } from "../components/dashboard/MetricCards";
import { SeedButton } from "../components/ui/SeedButton";
import { listAudit, listInvoices, verifyAudit } from "../lib/api";
import { formatINR } from "../lib/format";
import type { AuditVerification, InvoiceRow } from "../lib/types";

export default async function HomePage() {
  let invoices: InvoiceRow[] = [];
  let auditTotal = 0;
  let verification: AuditVerification | null = null;
  let error: string | null = null;

  try {
    const [invRes, auditRes, verifyRes] = await Promise.all([
      listInvoices(),
      listAudit({ limit: 1 }),
      verifyAudit().catch(() => null),
    ]);
    invoices = invRes.data;
    auditTotal = auditRes.meta.total_count ?? 0;
    verification = verifyRes ? verifyRes.data : null;
  } catch (exc) {
    error = exc instanceof Error ? exc.message : "API unavailable";
  }

  const overdue = invoices.filter((row) => row.status === "overdue" || row.state === "overdue");
  const atRisk = overdue.reduce(
    (sum, row) => sum + Number(row.outstanding_amount ?? Math.max(0, Number(row.total_amount) - Number(row.amount_paid))),
    0
  );

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

      {/* Metric Cards Grid - 4 Columns showcasing Audit Differentiator */}
      <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          label="Invoices Loaded"
          value={String(invoices.length)}
          type="loaded"
          hint="Total receivables in portfolio"
        />
        <MetricCard
          label="Overdue Queue"
          value={String(overdue.length)}
          type="overdue"
          hint="Active collection workload"
        />
        <MetricCard
          label="₹ Amount At Risk"
          value={formatINR(atRisk)}
          type="risk"
          hint="Overdue receivables balance"
        />
        <Link href="/audit" className="block group transition-transform hover:-translate-y-0.5">
          <div className="glass-card h-full rounded-2xl p-5 border border-emerald-500/30 bg-emerald-950/10 group-hover:border-emerald-500/60 transition-all">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-emerald-400">Policy Audit Log</span>
              <span className="rounded-full bg-emerald-500/20 px-2 py-0.5 text-[10px] font-extrabold text-emerald-300">
                {verification?.valid ? "Chain Verified ✓" : "SHA-256"}
              </span>
            </div>
            <div className="mt-3 text-2xl sm:text-3xl font-extrabold text-white font-mono">
              {auditTotal}
            </div>
            <div className="mt-1 flex items-center justify-between text-xs text-slate-400">
              <span>Cryptographic state transitions</span>
              <span className="text-emerald-400 font-bold group-hover:translate-x-1 transition-transform">View →</span>
            </div>
          </div>
        </Link>
      </div>

      {/* Aging Distribution */}
      <AgingBuckets invoices={invoices} />

      {/* Quick Summary Architecture Grid with SVG Icons */}
      <div className="grid gap-6 md:grid-cols-3">
        {/* Guardrails Card */}
        <div className="glass-card rounded-3xl p-6 transition-all hover:border-emerald-500/30">
          <div className="flex items-center gap-3 mb-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-emerald-500/15 border border-emerald-400/30 text-emerald-400 shadow-sm">
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
              </svg>
            </div>
            <h3 className="text-sm font-bold text-white">Deterministic Guardrails</h3>
          </div>
          <p className="text-xs text-slate-300 leading-relaxed">
            The state machine strictly caps outreach to max 3 contacts/week, respects opt-outs permanently, and pauses automation on promises or disputes.
          </p>
        </div>

        {/* Razorpay Links Card */}
        <div className="glass-card rounded-3xl p-6 transition-all hover:border-sky-500/30">
          <div className="flex items-center gap-3 mb-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-sky-500/15 border border-sky-400/30 text-sky-400 shadow-sm">
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </div>
            <h3 className="text-sm font-bold text-white">Razorpay Payment Links</h3>
          </div>
          <p className="text-xs text-slate-300 leading-relaxed">
            Automated nudges embed instant Razorpay payment links in WhatsApp messages, accelerating self-cure rates while preserving merchant trust.
          </p>
        </div>

        {/* Cryptographic Audit Card */}
        <div className="glass-card rounded-3xl p-6 transition-all hover:border-purple-500/30">
          <div className="flex items-center gap-3 mb-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-purple-500/15 border border-purple-400/30 text-purple-400 shadow-sm">
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
              </svg>
            </div>
            <h3 className="text-sm font-bold text-white">SHA-256 Tamper-Evidence</h3>
          </div>
          <p className="text-xs text-slate-300 leading-relaxed">
            Every state transition is signed in a continuous SHA-256 Merkle chain, providing mathematical proof of zero retro-active log tampering.
          </p>
        </div>
      </div>
    </div>
  );
}
