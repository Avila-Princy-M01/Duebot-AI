import { BuyerTableInteractive } from "../../components/buyers/BuyerTableInteractive";
import { listBuyers } from "../../lib/api";

export default async function BuyersPage() {
  const payload = await listBuyers();
  const buyers = payload.data;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-2xl font-extrabold tracking-tight text-white">Buyer Relationship Directory</h1>
          <p className="text-xs text-slate-400">
            Track B2B customer payment history, reliability tiers, and contact preferences.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <span className="rounded-xl border border-slate-800 bg-panel px-3 py-1.5 text-xs font-bold text-sky-400">
            {buyers.length} Buyers Onboarded
          </span>
        </div>
      </div>

      <BuyerTableInteractive buyers={buyers} />
    </div>
  );
}
