import { InvoiceTableInteractive } from "../../components/invoices/InvoiceTableInteractive";
import { listInvoices } from "../../lib/api";

export default async function InvoicesPage() {
  const payload = await listInvoices();
  const invoices = payload.data;

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

      <InvoiceTableInteractive initialInvoices={invoices} />
    </div>
  );
}
