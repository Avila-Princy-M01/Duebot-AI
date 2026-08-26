import { InvoiceTableInteractive } from "../../components/invoices/InvoiceTableInteractive";
import { listInvoices } from "../../lib/api";
import type { InvoiceRow } from "../../lib/types";

export default async function InvoicesPage() {
  let invoices: InvoiceRow[] = [];
  let error: string | null = null;

  try {
    const payload = await listInvoices();
    invoices = payload?.data ?? [];
  } catch (exc) {
    error = exc instanceof Error ? exc.message : "Failed to load invoices";
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-2xl font-extrabold tracking-tight text-white">Invoice Receivables Ledger</h1>
          <p className="text-xs text-slate-400">
            View status, aging, risk tiers, and launch instant WhatsApp nudge previews.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <span className="rounded-xl border border-slate-800 bg-panel px-3 py-1.5 text-xs font-bold text-sky-400">
            {invoices.length} Total Invoices
          </span>
        </div>
      </div>

      {error ? (
        <div className="rounded-2xl border border-amber-500/40 bg-amber-950/30 p-5 text-xs text-amber-200 backdrop-blur-md" role="alert">
          <p className="font-bold">{error}</p>
          <p className="mt-1 text-slate-400">
            Ensure backend server is running on <code className="text-amber-300">http://localhost:8000</code>.
          </p>
        </div>
      ) : null}

      <InvoiceTableInteractive initialInvoices={invoices} />
    </div>
  );
}
