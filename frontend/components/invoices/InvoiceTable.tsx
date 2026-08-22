import type { InvoiceRow } from "../../lib/types";

interface InvoiceTableProps {
  invoices: InvoiceRow[];
}

export function InvoiceTable({ invoices }: InvoiceTableProps) {
  return (
    <div className="overflow-x-auto rounded-xl border border-slate-800">
      <table className="w-full text-left text-sm">
        <thead className="bg-panel text-slate-400">
          <tr>
            <th className="px-4 py-3">Invoice</th>
            <th className="px-4 py-3">State</th>
            <th className="px-4 py-3">Risk</th>
            <th className="px-4 py-3">Days overdue</th>
            <th className="px-4 py-3">Amount</th>
            <th className="px-4 py-3">Edge case</th>
          </tr>
        </thead>
        <tbody>
          {invoices.map((inv) => (
            <tr key={inv.invoice_id} className="border-t border-slate-800">
              <td className="px-4 py-3">
                <a className="text-sky-300 hover:underline" href={`/invoices/${inv.invoice_id}`}>
                  {inv.invoice_number}
                </a>
              </td>
              <td className="px-4 py-3 font-mono text-xs">{inv.state}</td>
              <td className="px-4 py-3">{inv.risk_tier}</td>
              <td className="px-4 py-3">{inv.days_overdue}</td>
              <td className="px-4 py-3">
                {inv.currency} {Number(inv.total_amount).toLocaleString("en-IN")}
              </td>
              <td className="px-4 py-3 text-slate-400">{inv.edge_case}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
