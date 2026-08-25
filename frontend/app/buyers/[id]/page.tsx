import { notFound } from "next/navigation";
import { BuyerVoiceBriefing } from "../../../components/buyers/BuyerVoiceBriefing";
import { getBuyer } from "../../../lib/api";

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
  return (
    <div className="space-y-6">
      <div className="rounded-2xl border border-slate-800/80 bg-panel/70 p-6 backdrop-blur-md">
        <h1 className="text-2xl font-extrabold tracking-tight text-white">{buyer.company_name}</h1>
        <p className="mt-1 text-xs text-slate-400">
          Contact: {buyer.contact_name} · Reliability: <span className="font-bold text-sky-400">{buyer.reliability_tier}</span> ·{" "}
          <span className="font-bold text-emerald-400">{(buyer.on_time_payment_rate * 100).toFixed(0)}% on-time</span>
        </p>
      </div>

      {/* Scoped Read-Only AI Voice Briefing */}
      <BuyerVoiceBriefing buyerId={buyer.buyer_id} />

      <div className="rounded-2xl border border-slate-800/80 bg-panel/70 p-6 backdrop-blur-md space-y-3">
        <h3 className="text-sm font-bold text-white">Associated Invoices</h3>
        <ul className="divide-y divide-slate-800/60 text-xs">
          {"invoices" in buyer
            ? buyer.invoices.map((inv) => (
                <li key={inv.invoice_id} className="py-3 flex items-center justify-between">
                  <a className="font-bold text-sky-400 hover:underline" href={`/invoices/${inv.invoice_id}`}>
                    {inv.invoice_number}
                  </a>
                  <span className="text-slate-300">₹{Number(inv.total_amount).toLocaleString("en-IN")}</span>
                  <span className="uppercase font-semibold text-slate-400">{inv.state}</span>
                  <span className="text-amber-400 font-medium">{inv.days_overdue} days overdue</span>
                </li>
              ))
            : null}
        </ul>
      </div>
    </div>
  );
}
