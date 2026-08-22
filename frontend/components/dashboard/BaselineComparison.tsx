import type { BaselineRow } from "../../lib/types";

interface BaselineComparisonProps {
  rows: BaselineRow[];
}

function pct(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

export function BaselineComparison({ rows }: BaselineComparisonProps) {
  return (
    <div className="overflow-x-auto rounded-xl border border-slate-800">
      <table className="w-full text-left text-sm">
        <thead className="bg-panel text-slate-400">
          <tr>
            <th className="px-4 py-3">Strategy</th>
            <th className="px-4 py-3">N</th>
            <th className="px-4 py-3">Recovery</th>
            <th className="px-4 py-3">30d</th>
            <th className="px-4 py-3">Contacts</th>
            <th className="px-4 py-3">₹ recovered</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.id} className="border-t border-slate-800">
              <td className="px-4 py-3 font-medium">{row.strategy}</td>
              <td className="px-4 py-3">{row.eval_set_size}</td>
              <td className="px-4 py-3">{pct(row.recovered_count / Math.max(row.eval_set_size, 1))}</td>
              <td className="px-4 py-3">{pct(row.recovery_30d)}</td>
              <td className="px-4 py-3">{row.total_contacts_sent}</td>
              <td className="px-4 py-3">{Number(row.recovered_value).toLocaleString("en-IN")}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
