import { getBuyer } from "../../../lib/api";

interface BuyerDetailPageProps {
  params: { id: string };
}

export async function BuyerDetailPage({ params }: BuyerDetailPageProps) {
  const payload = await getBuyer(params.id);
  const buyer = payload.data;
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">{buyer.company_name}</h1>
      <p className="text-slate-400">
        {buyer.contact_name} · {buyer.reliability_tier} ·{" "}
        {(buyer.on_time_payment_rate * 100).toFixed(0)}% on-time
      </p>
      <ul className="space-y-2 text-sm">
        {"invoices" in buyer
          ? buyer.invoices.map((inv) => (
              <li key={inv.invoice_id}>
                <a className="text-sky-300 hover:underline" href={`/invoices/${inv.invoice_id}`}>
                  {inv.invoice_number}
                </a>{" "}
                · {inv.state} · {inv.days_overdue}d
              </li>
            ))
          : null}
      </ul>
    </div>
  );
}

export default BuyerDetailPage;
