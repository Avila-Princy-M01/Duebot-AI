import { BuyerTableInteractive } from "../../components/buyers/BuyerTableInteractive";
import { listBuyers } from "../../lib/api";
import type { BuyerRow } from "../../lib/types";

export default async function BuyersPage() {
  let buyers: BuyerRow[] = [];
  let error: string | null = null;

  try {
    const payload = await listBuyers();
    buyers = payload?.data ?? [];
  } catch (exc) {
    error = exc instanceof Error ? exc.message : "Failed to load buyers";
  }

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

      {error ? (
        <div className="rounded-2xl border border-amber-500/40 bg-amber-950/30 p-5 text-xs text-amber-200 backdrop-blur-md" role="alert">
          <p className="font-bold">{error}</p>
          <p className="mt-1 text-slate-400">
            Ensure backend server is running on <code className="text-amber-300">http://localhost:8000</code>.
          </p>
        </div>
      ) : null}

      <BuyerTableInteractive buyers={buyers} />
    </div>
  );
}
