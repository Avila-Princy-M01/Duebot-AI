import type { AuditRow } from "../../lib/types";
import { formatTimestamp } from "../../lib/format";

interface AuditLogProps {
  rows: AuditRow[];
}

export function AuditLog({ rows }: AuditLogProps) {
  return (
    <div className="glass-panel overflow-hidden rounded-3xl">
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead className="border-b border-white/[0.08] bg-slate-900/80 text-slate-400 font-bold uppercase tracking-wider">
            <tr>
              <th className="px-4 py-3.5">Timestamp (UTC)</th>
              <th className="px-4 py-3.5">Invoice #</th>
              <th className="px-4 py-3.5">Transition & Event</th>
              <th className="px-4 py-3.5">Actor</th>
              <th className="px-4 py-3.5">Policy Reasoning & Metadata</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/[0.06] font-sans">
            {rows.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-slate-500">
                  No audit transitions match the selected criteria.
                </td>
              </tr>
            ) : (
              rows.map((row) => {
                const meta = row.extra_metadata as Record<string, unknown> | null;
                const confidence = meta?.confidence as number | undefined;
                const intent = meta?.intent as string | undefined;
                const eventName = (meta?.event as string | undefined) ?? "";
                const policyVersion = (meta?.policy_version as string | undefined) ?? "v1.0.0";
                const promisedDate = meta?.promised_date as string | undefined;
                const resolution = meta?.resolution as string | undefined;
                const actorRole = meta?.actor_role as string | undefined;

                const actorBadge =
                  row.actor === "human"
                    ? "bg-amber-500/10 border-amber-500/30 text-amber-300"
                    : row.actor === "agent"
                      ? "bg-sky-500/10 border-sky-500/30 text-sky-300"
                      : "bg-emerald-500/10 border-emerald-500/30 text-emerald-300";

                return (
                  <tr key={row.id} className="transition-colors hover:bg-white/[0.03] align-top">
                    <td className="px-4 py-3.5 font-mono text-[11px] text-slate-400 whitespace-nowrap">
                      {formatTimestamp(row.occurred_at)}
                    </td>
                    <td className="px-4 py-3.5 font-mono font-bold text-sky-400">
                      <a href={`/invoices/${row.invoice_id}`} className="hover:underline">
                        {row.invoice_id}
                      </a>
                    </td>
                    <td className="px-4 py-3.5 whitespace-nowrap space-y-1">
                      <div className="inline-flex items-center gap-1.5 font-mono text-xs">
                        <span className="rounded bg-slate-800 px-2 py-0.5 text-slate-300 font-semibold text-[10px] uppercase">
                          {row.from_state}
                        </span>
                        <span className="text-sky-400 font-bold">→</span>
                        <span className="rounded bg-sky-500/20 border border-sky-500/30 px-2 py-0.5 text-sky-300 font-bold text-[10px] uppercase">
                          {row.to_state}
                        </span>
                      </div>
                      {eventName ? (
                        <div>
                          <span className="inline-block rounded-md bg-indigo-500/10 border border-indigo-500/20 px-1.5 py-0.5 font-mono text-[9px] font-medium text-indigo-300">
                            event: {eventName}
                          </span>
                        </div>
                      ) : null}
                    </td>
                    <td className="px-4 py-3.5">
                      <div className="space-y-1">
                        <span
                          className={`inline-block rounded border px-2 py-0.5 text-[10px] font-extrabold uppercase ${actorBadge}`}
                        >
                          {row.actor}
                        </span>
                        {actorRole ? (
                          <div className="text-[9px] font-medium text-slate-400">{actorRole}</div>
                        ) : null}
                      </div>
                    </td>
                    <td className="px-4 py-3.5 space-y-2">
                      <p className="text-slate-200 text-xs font-medium leading-relaxed">
                        {row.reasoning_summary}
                      </p>

                      <div className="flex flex-wrap items-center gap-2 pt-0.5">
                        {policyVersion ? (
                          <span className="rounded bg-slate-800/80 border border-slate-700/50 px-1.5 py-0.5 font-mono text-[9px] text-slate-400">
                            policy: {policyVersion}
                          </span>
                        ) : null}

                        {(confidence !== undefined && confidence !== null) ? (
                          <span className="inline-flex items-center gap-1 rounded bg-amber-500/10 border border-amber-500/30 px-2 py-0.5 font-mono text-[10px] font-bold text-amber-300">
                            <span>Confidence: {(Number(confidence) * 100).toFixed(0)}%</span>
                            <span className="text-slate-500">|</span>
                            <span className="text-slate-400">Threshold: 70%</span>
                            {Number(confidence) < 0.7 ? (
                              <span className="ml-1 rounded bg-rose-500/20 px-1 text-rose-300 uppercase font-extrabold text-[9px]">
                                Abstained
                              </span>
                            ) : (
                              <span className="ml-1 rounded bg-emerald-500/20 px-1 text-emerald-300 uppercase font-extrabold text-[9px]">
                                Accepted
                              </span>
                            )}
                          </span>
                        ) : null}

                        {intent ? (
                          <span className="rounded bg-slate-800 px-2 py-0.5 font-mono text-[10px] text-slate-300">
                            intent: <span className="text-sky-300 font-semibold">{intent}</span>
                          </span>
                        ) : null}

                        {promisedDate ? (
                          <span className="rounded bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 font-mono text-[10px] text-emerald-300">
                            target: {promisedDate}
                          </span>
                        ) : null}

                        {resolution ? (
                          <span className="rounded bg-purple-500/10 border border-purple-500/20 px-2 py-0.5 font-mono text-[10px] text-purple-300">
                            resolution: {resolution}
                          </span>
                        ) : null}
                      </div>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default AuditLog;
