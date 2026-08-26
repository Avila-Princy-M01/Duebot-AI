import { notFound } from "next/navigation";
import { BuyerVoiceBriefing } from "../../../components/buyers/BuyerVoiceBriefing";
import { getBuyer } from "../../../lib/api";
import { formatDateShort, formatINR } from "../../../lib/format";

interface BuyerDetailPageProps {
  params: { id: string };
}

export default async function BuyerDetailPage({ params }: BuyerDetailPageProps) {
  let buyer;
  try {
    const payload = await getBuyer(params.id);
    buyer = payload?.data;
  } catch {
    notFound();
  }
  if (!buyer) {
    notFound();
  }

  const invoices = "invoices" in buyer ? buyer.invoices : [];
  const totalInvoiced = invoices.reduce((sum, i) => sum + Number(i.total_amount), 0);
  const totalOutstanding = invoices.reduce((sum, i) => sum + Number(i.outstanding_amount), 0);
  const overdueCount = invoices.filter((i) => i.days_overdue > 0).length;

  return (
    <div className="space-y-6">
      {/* Top Banner with Direct Portfolio Metrics */}
      <div className="glass-panel rounded-3xl p-6 sm:p-8 backdrop-blur-md flex flex-col md:flex-row md:items-center md:justify-between gap-4 border border-white/[0.08] shadow-xl">
        <div className="space-y-1.5">
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white">{buyer.company_name}</h1>
            <span className="rounded-full border border-sky-500/30 bg-sky-500/10 px-2.5 py-0.5 text-xs font-extrabold uppercase text-sky-300">
              {buyer.reliability_tier.replace(/_/g, " ")}
            </span>
          </div>
          <p className="text-xs text-slate-300">
            Primary Contact: <span className="font-semibold text-white">{buyer.contact_name}</span> · Partner Since: <span className="text-slate-300">{buyer.relationship_since ? formatDateShort(buyer.relationship_since) : "2024"}</span> · Historic On-Time: <span className="font-bold text-emerald-400">{Math.round(buyer.on_time_payment_rate * 100)}%</span>
          </p>
        </div>

        {/* Aggregate Financial Metrics */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="glass-card rounded-2xl p-3 px-4 border border-slate-700 text-center">
            <div className="text-[11px] font-bold uppercase text-slate-400">Total Billed</div>
            <div className="font-mono text-sm font-extrabold text-white mt-0.5">{formatINR(totalInvoiced)}</div>
          </div>
          <div className="glass-card rounded-2xl p-3 px-4 border border-amber-500/30 bg-amber-950/20 text-center">
            <div className="text-[11px] font-bold uppercase text-amber-400">Outstanding</div>
            <div className="font-mono text-sm font-extrabold text-amber-300 mt-0.5">{formatINR(totalOutstanding)}</div>
          </div>
          <div className="glass-card rounded-2xl p-3 px-4 border border-slate-700 text-center">
            <div className="text-[11px] font-bold uppercase text-slate-400">Invoices</div>
            <div className="font-mono text-sm font-extrabold text-sky-400 mt-0.5">{invoices.length} ({overdueCount} overdue)</div>
          </div>
        </div>
      </div>

      {/* AI Intelligence Voice & Action Briefing */}
      <BuyerVoiceBriefing buyerId={buyer.buyer_id} />

      {/* Associated Invoices Ledger Section */}
      <div className="glass-panel rounded-3xl p-6 sm:p-7 backdrop-blur-md space-y-4 border border-white/[0.08] shadow-xl">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-sm font-extrabold text-white uppercase tracking-wider">Associated Receivables</h3>
            <p className="text-xs text-slate-400">All open and historical invoices issued to {buyer.company_name}.</p>
          </div>
          <span className="rounded-xl border border-slate-700 bg-slate-800/80 px-3 py-1 text-xs font-bold text-slate-300">
            {invoices.length} Invoices
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="border-b border-white/[0.08] bg-slate-900/90 text-slate-300 font-bold uppercase tracking-wider">
              <tr>
                <th className="px-4 py-3">Invoice #</th>
                <th className="px-4 py-3">Total Amount</th>
                <th className="px-4 py-3">Outstanding</th>
                <th className="px-4 py-3">Due Date</th>
                <th className="px-4 py-3">Lifecycle State</th>
                <th className="px-4 py-3">Aging</th>
                <th className="px-4 py-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.06] font-sans">
              {invoices.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-slate-400 text-xs">
                    No invoices associated with this buyer account.
                  </td>
                </tr>
              ) : (
                invoices.map((inv) => (
                  <tr key={inv.invoice_id} className="transition-colors hover:bg-white/[0.03]">
                    <td className="px-4 py-3.5 font-mono font-bold text-sky-400">
                      <a className="hover:underline" href={`/invoices/${inv.invoice_id}`}>
                        {inv.invoice_number}
                      </a>
                    </td>
                    <td className="px-4 py-3.5 font-mono text-slate-200">
                      {formatINR(inv.total_amount)}
                    </td>
                    <td className="px-4 py-3.5 font-mono">
                      {Number(inv.outstanding_amount) > 0 ? (
                        <span className="font-bold text-amber-300">{formatINR(inv.outstanding_amount)}</span>
                      ) : (
                        <span className="font-bold uppercase text-emerald-400">Settled</span>
                      )}
                    </td>
                    <td className="px-4 py-3.5 text-slate-300">
                      {formatDateShort(inv.due_date)}
                    </td>
                    <td className="px-4 py-3.5">
                      <span className="rounded bg-slate-800 border border-slate-700 px-2 py-0.5 font-mono text-xs font-semibold uppercase text-slate-200">
                        {inv.state.replace(/_/g, " ")}
                      </span>
                    </td>
                    <td className="px-4 py-3.5">
                      {inv.days_overdue > 0 ? (
                        <span className="font-bold text-rose-400">{inv.days_overdue}d overdue</span>
                      ) : (
                        <span className="text-slate-400">Current</span>
                      )}
                    </td>
                    <td className="px-4 py-3.5 text-right">
                      <a
                        href={`/invoices/${inv.invoice_id}`}
                        className="rounded-xl border border-sky-500/30 bg-sky-500/10 px-3 py-1 text-xs font-bold text-sky-300 hover:bg-sky-500 hover:text-white transition-all"
                      >
                        View Details →
                      </a>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
