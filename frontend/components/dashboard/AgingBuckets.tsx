import type { InvoiceRow } from "../../lib/types";

interface AgingBucketsProps {
  invoices: InvoiceRow[];
}

function bucket(days: number): string {
  if (days <= 0) return "Current";
  if (days <= 30) return "0–30";
  if (days <= 60) return "31–60";
  if (days <= 90) return "61–90";
  return "90+";
}

export function AgingBuckets({ invoices }: AgingBucketsProps) {
  const groups: Record<string, number> = {
    Current: 0,
    "0–30": 0,
    "31–60": 0,
    "61–90": 0,
    "90+": 0,
  };
  for (const inv of invoices) {
    const key = bucket(inv.days_overdue);
    groups[key] = (groups[key] ?? 0) + 1;
  }
  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
      {Object.entries(groups).map(([name, count]) => (
        <div key={name} className="rounded-lg border border-slate-800 bg-panel px-4 py-3">
          <p className="text-xs text-slate-400">{name}</p>
          <p className="text-xl font-semibold">{count}</p>
        </div>
      ))}
    </div>
  );
}
