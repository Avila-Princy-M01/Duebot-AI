import type { AuditRow } from "../../lib/types";

interface AuditLogProps {
  rows: AuditRow[];
}

export function AuditLog({ rows }: AuditLogProps) {
  return (
    <div className="overflow-x-auto rounded-xl border border-slate-800">
      <table className="w-full text-left text-sm">
        <thead className="bg-panel text-slate-400">
          <tr>
            <th className="px-4 py-3">When</th>
            <th className="px-4 py-3">Invoice</th>
            <th className="px-4 py-3">Transition</th>
            <th className="px-4 py-3">Actor</th>
            <th className="px-4 py-3">Why</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.id} className="border-t border-slate-800 align-top">
              <td className="px-4 py-3 text-xs text-slate-400">{row.occurred_at}</td>
              <td className="px-4 py-3 font-mono text-xs">{row.invoice_id}</td>
              <td className="px-4 py-3 font-mono text-xs">
                {row.from_state} → {row.to_state}
              </td>
              <td className="px-4 py-3">{row.actor}</td>
              <td className="px-4 py-3">{row.reasoning_summary}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
