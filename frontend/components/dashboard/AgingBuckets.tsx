import type { InvoiceRow } from "../../lib/types";

interface AgingBucketsProps {
  invoices: InvoiceRow[];
}

function bucket(days: number): string {
  if (days <= 0) return "Current";
  if (days <= 30) return "0–30 days";
  if (days <= 60) return "31–60 days";
  if (days <= 90) return "61–90 days";
  return "90+ days";
}

const BUCKET_THEMES: Record<string, { color: string; bg: string; border: string; bar: string }> = {
  Current: {
    color: "text-emerald-400",
    bg: "bg-emerald-500/10",
    border: "border-emerald-500/20 hover:border-emerald-500/40",
    bar: "bg-gradient-to-r from-emerald-500 to-teal-400",
  },
  "0–30 days": {
    color: "text-sky-400",
    bg: "bg-sky-500/10",
    border: "border-sky-500/20 hover:border-sky-500/40",
    bar: "bg-gradient-to-r from-sky-500 to-blue-500",
  },
  "31–60 days": {
    color: "text-indigo-400",
    bg: "bg-indigo-500/10",
    border: "border-indigo-500/20 hover:border-indigo-500/40",
    bar: "bg-gradient-to-r from-indigo-500 to-purple-500",
  },
  "61–90 days": {
    color: "text-amber-400",
    bg: "bg-amber-500/10",
    border: "border-amber-500/20 hover:border-amber-500/40",
    bar: "bg-gradient-to-r from-amber-500 to-orange-500",
  },
  "90+ days": {
    color: "text-rose-400",
    bg: "bg-rose-500/10",
    border: "border-rose-500/20 hover:border-rose-500/40",
    bar: "bg-gradient-to-r from-rose-500 to-red-600",
  },
};

export function AgingBuckets({ invoices }: AgingBucketsProps) {
  const groups: Record<string, number> = {
    Current: 0,
    "0–30 days": 0,
    "31–60 days": 0,
    "61–90 days": 0,
    "90+ days": 0,
  };

  for (const inv of invoices) {
    const key = bucket(inv.days_overdue);
    groups[key] = (groups[key] ?? 0) + 1;
  }

  const maxCount = Math.max(...Object.values(groups), 1);
  const totalInvoices = Math.max(invoices.length, 1);

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-bold text-slate-300 uppercase tracking-wider">Receivables Aging Distribution</h3>
        <span className="text-xs text-slate-500">Total: {invoices.length} invoices</span>
      </div>

      <div className="grid grid-cols-2 gap-3.5 md:grid-cols-5">
        {Object.entries(groups).map(([name, count]) => {
          const theme = BUCKET_THEMES[name] || BUCKET_THEMES["Current"]!;
          const pct = Math.round((count / totalInvoices) * 100);
          const barPct = Math.round((count / maxCount) * 100);

          return (
            <div
              key={name}
              className={`group relative overflow-hidden rounded-2xl border ${theme.border} bg-panel/80 p-4 transition-all duration-200 hover:-translate-y-1 hover:shadow-lg shadow-black/30`}
            >
              <div className="flex items-center justify-between">
                <p className="text-xs font-semibold text-slate-400">{name}</p>
                <span className={`text-[11px] font-bold ${theme.color}`}>{pct}%</span>
              </div>

              <p className={`mt-2 text-2xl font-extrabold tracking-tight ${theme.color}`}>{count}</p>

              <div className="mt-3 h-1.5 w-full overflow-hidden rounded-full bg-slate-800">
                <div
                  className={`h-full rounded-full ${theme.bar} transition-all duration-500`}
                  style={{ width: `${barPct}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default AgingBuckets;
