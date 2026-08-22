import { listBuyers } from "../../lib/api";

export async function BuyersPage() {
  const payload = await listBuyers();
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Buyers</h1>
      <div className="overflow-x-auto rounded-xl border border-slate-800">
        <table className="w-full text-left text-sm">
          <thead className="bg-panel text-slate-400">
            <tr>
              <th className="px-4 py-3">Company</th>
              <th className="px-4 py-3">Contact</th>
              <th className="px-4 py-3">Reliability</th>
              <th className="px-4 py-3">On-time rate</th>
            </tr>
          </thead>
          <tbody>
            {payload.data.map((buyer) => (
              <tr key={buyer.buyer_id} className="border-t border-slate-800">
                <td className="px-4 py-3">
                  <a className="text-sky-300 hover:underline" href={`/buyers/${buyer.buyer_id}`}>
                    {buyer.company_name}
                  </a>
                </td>
                <td className="px-4 py-3">{buyer.contact_name}</td>
                <td className="px-4 py-3">{buyer.reliability_tier}</td>
                <td className="px-4 py-3">{(buyer.on_time_payment_rate * 100).toFixed(0)}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default BuyersPage;
