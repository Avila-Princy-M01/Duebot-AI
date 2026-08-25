import { formatINR } from "../../lib/format";
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
              className={`relative overflow-hidden rounded-3xl p-6 transition-all duration-300 hover:-translate-y-1.5 ${
                isDuebot
                  ? "glass-card-glow border-sky-400/40"
                  : "glass-card border-white/[0.08]"
              }`}
            >
              {isDuebot ? (
                <div className="absolute top-0 right-0 rounded-bl-2xl bg-gradient-to-r from-sky-500 via-blue-600 to-indigo-600 px-3.5 py-1 text-[10px] font-extrabold uppercase tracking-wider text-white shadow-lg shadow-sky-500/30">
                  ★ RECOMMENDED
                </div>
              ) : null}

              <p className="text-[11px] font-bold uppercase tracking-wider text-slate-400">{row.strategy.replace("_", " ")}</p>

              <div className="mt-4 flex items-baseline justify-between">
                <div>
                  <span className={`text-3xl font-extrabold tracking-tight ${isDuebot ? "text-white" : "text-slate-200"}`}>{pct(recRate)}</span>
                  <span className="ml-2 text-xs text-slate-400 font-medium">Recovery Rate</span>
                </div>
              </div>

              {/* Progress bar */}
              <div className="mt-3.5 h-2 w-full overflow-hidden rounded-full bg-slate-900 shadow-inner">
                <div
                  className={`h-full rounded-full transition-all duration-500 ${
                    isDuebot
                      ? "bg-gradient-to-r from-sky-400 via-blue-500 to-indigo-500 shadow-sm shadow-sky-500/50"
                      : "bg-slate-700"
                  }`}
                  style={{ width: `${Math.round(recRate * 100)}%` }}
                />
              </div>

              <div className="mt-6 space-y-2.5 border-t border-white/[0.07] pt-4 text-xs">
                <div className="flex items-center justify-between text-slate-400">
                  <span>30-Day Recovery:</span>
                  <span className="font-bold text-white">{pct(row.recovery_30d)}</span>
                </div>
                <div className="flex items-center justify-between text-slate-400">
                  <span>Avg Days to Recovery:</span>
                  <span className="font-mono font-bold text-amber-300">
                    {Number(row.avg_days_to_recovery ?? 0).toFixed(1)} days
                  </span>
                </div>
                <div className="flex items-center justify-between text-slate-400">
                  <span>Contacts Sent:</span>
                  <span className="font-mono font-bold text-white">{row.total_contacts_sent}</span>
                </div>
                <div className="flex items-center justify-between text-slate-400">
                  <span>Total Recovered:</span>
                  <span className="font-mono font-bold text-emerald-400">{formatINR(recValue)}</span>
                </div>
                <div className="flex items-center justify-between text-slate-400 pt-1">
                  <span className="font-semibold text-slate-300">Capital Efficiency:</span>
                  <span className="font-mono font-extrabold text-sky-400">
                    {perContact > 0 ? `${formatINR(Math.round(perContact))} / contact` : "N/A"}
                  </span>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Comparison Table */}
      <div className="glass-panel overflow-hidden rounded-3xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="border-b border-slate-800 bg-panel/90 text-slate-400 font-bold uppercase tracking-wider">
              <tr>
                <th className="px-4 py-3.5">Strategy</th>
                <th className="px-4 py-3.5">Eval Set Size</th>
                <th className="px-4 py-3.5">Recovery Rate</th>
                <th className="px-4 py-3.5">30-Day Recovery</th>
                <th className="px-4 py-3.5">Avg Days to Pay</th>
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
                  <td className="px-4 py-3.5 font-bold text-amber-400">
                    {Number(row.avg_days_to_recovery ?? 0).toFixed(1)}d
                  </td>
                  <td className="px-4 py-3.5 text-slate-300">{row.total_contacts_sent}</td>
                  <td className="px-4 py-3.5 font-bold text-emerald-400">
                    {formatINR(row.recovered_value)}
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
