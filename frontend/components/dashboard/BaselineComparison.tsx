import type { BaselineRow } from "../../lib/types";

interface BaselineComparisonProps {
  rows: BaselineRow[];
}

function pct(val: number): string {
  return `${(val * 100).toFixed(1)}%`;
}

export function BaselineComparison({ rows }: BaselineComparisonProps) {
  return (
    <div className="space-y-6">
      {/* Visual Strategy Comparison Cards */}
      <div className="grid gap-4 md:grid-cols-3">
        {rows.map((row) => {
          const isDuebot = row.strategy.toLowerCase() === "duebot";
          const recRate = row.eval_set_size > 0 ? row.recovered_count / row.eval_set_size : 0;
          const recValue = Number(row.recovered_value);
          const perContact = row.total_contacts_sent > 0 ? recValue / row.total_contacts_sent : 0;

          return (
            <div
              key={row.id}
              className={`relative overflow-hidden rounded-2xl border ${
                isDuebot
                  ? "border-sky-500/40 bg-gradient-to-b from-sky-950/40 via-panel to-panel shadow-2xl shadow-sky-950/40"
                  : "border-slate-800/80 bg-panel/70"
              } p-6 backdrop-blur-md transition-all hover:-translate-y-1`}
            >
              {isDuebot ? (
                <div className="absolute top-0 right-0 rounded-bl-xl bg-gradient-to-r from-sky-500 to-blue-600 px-3 py-1 text-[10px] font-extrabold uppercase text-white shadow-md">
                  ★ RECOMMENDED
                </div>
              ) : null}

              <p className="text-xs font-bold uppercase tracking-wider text-slate-400">{row.strategy.replace("_", " ")}</p>

              <div className="mt-4 flex items-baseline justify-between">
                <div>
                  <span className="text-3xl font-extrabold text-white">{pct(recRate)}</span>
                  <span className="ml-2 text-xs text-slate-400">Recovery Rate</span>
                </div>
              </div>

              {/* Progress bar */}
              <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-slate-800">
                <div
                  className={`h-full rounded-full ${
                    isDuebot
                      ? "bg-gradient-to-r from-sky-400 via-blue-500 to-indigo-500"
                      : "bg-slate-600"
                  }`}
                  style={{ width: `${Math.round(recRate * 100)}%` }}
                />
              </div>

              <div className="mt-6 space-y-2 border-t border-slate-800/80 pt-4 text-xs">
                <div className="flex items-center justify-between text-slate-400">
                  <span>30-Day Recovery:</span>
                  <span className="font-bold text-white">{pct(row.recovery_30d)}</span>
                </div>
                <div className="flex items-center justify-between text-slate-400">
                  <span>Contacts Sent:</span>
                  <span className="font-mono font-bold text-white">{row.total_contacts_sent}</span>
                </div>
                <div className="flex items-center justify-between text-slate-400">
                  <span>Total Recovered:</span>
                  <span className="font-mono font-bold text-emerald-400">₹{recValue.toLocaleString("en-IN")}</span>
                </div>
                <div className="flex items-center justify-between text-slate-400 pt-1">
                  <span className="font-semibold">Capital Efficiency:</span>
                  <span className="font-mono font-extrabold text-sky-400">
                    {perContact > 0 ? `₹${Math.round(perContact).toLocaleString("en-IN")} / contact` : "N/A"}
                  </span>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Comparison Table */}
      <div className="overflow-hidden rounded-2xl border border-slate-800/80 bg-panel/60 backdrop-blur-md shadow-xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="border-b border-slate-800 bg-panel/90 text-slate-400 font-bold uppercase tracking-wider">
              <tr>
                <th className="px-4 py-3.5">Strategy</th>
                <th className="px-4 py-3.5">Eval Set Size</th>
                <th className="px-4 py-3.5">Recovery Rate</th>
                <th className="px-4 py-3.5">30-Day Recovery</th>
                <th className="px-4 py-3.5">Contacts Sent</th>
                <th className="px-4 py-3.5">Total Recovered Value</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono">
              {rows.map((row) => (
                <tr key={row.id} className="transition-colors hover:bg-slate-800/40">
                  <td className="px-4 py-3.5 font-sans font-bold text-white">{row.strategy}</td>
                  <td className="px-4 py-3.5 text-slate-300">{row.eval_set_size}</td>
                  <td className="px-4 py-3.5 font-bold text-sky-400">
                    {pct(row.recovered_count / Math.max(row.eval_set_size, 1))}
                  </td>
                  <td className="px-4 py-3.5 text-slate-300">{pct(row.recovery_30d)}</td>
                  <td className="px-4 py-3.5 text-slate-300">{row.total_contacts_sent}</td>
                  <td className="px-4 py-3.5 font-bold text-emerald-400">
                    ₹{Number(row.recovered_value).toLocaleString("en-IN")}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

export default BaselineComparison;
