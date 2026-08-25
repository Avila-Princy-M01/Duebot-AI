import { formatDate, formatINR, formatTimestamp } from "../../lib/format";
import type { InvoiceDetail } from "../../lib/types";

const STATUS_STYLES: Record<string, string> = {
  pending: "border-amber-500/30 bg-amber-500/10 text-amber-300",
  kept: "border-emerald-500/30 bg-emerald-500/10 text-emerald-300",
  broken: "border-rose-500/30 bg-rose-500/10 text-rose-300",
};

interface PromiseListProps {
  promises: InvoiceDetail["promises"];
  promiseOutcome: string;
}

export function PromiseList({ promises, promiseOutcome }: PromiseListProps) {
  return (
    <section className="rounded-2xl border border-slate-800/80 bg-panel/70 p-5 backdrop-blur-md shadow-lg space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 pb-3">
        <h3 className="flex items-center gap-2 text-sm font-bold text-white">
          <span className="h-2 w-2 rounded-full bg-amber-400" />
          Promise-to-Pay Tracking ({promises.length})
        </h3>
        <span className="font-mono text-[11px] text-slate-500">ground truth: {promiseOutcome}</span>
      </div>

      {promises.length === 0 ? (
        <p className="py-4 text-center text-xs text-slate-500">
          No promise logged. DueBot only records a promise above 70% parser confidence, so an
          ambiguous reply abstains by design.
        </p>
      ) : (
        <ol className="space-y-3">
          {promises.map((promise) => {
            const style =
              STATUS_STYLES[promise.status] ?? "border-slate-700 bg-slate-800/60 text-slate-300";
            return (
              <li
                key={promise.id}
                className="rounded-xl border border-slate-800/80 bg-slate-900/80 p-3.5 space-y-2"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="text-xs font-semibold text-slate-200">
                    Promised {formatDate(promise.promised_date)}
                    {promise.promised_amount ? (
                      <span className="ml-1.5 font-mono font-bold text-white">
                        {formatINR(promise.promised_amount)}
                      </span>
                    ) : null}
                  </span>
                  <span
                    className={`rounded border px-2 py-0.5 text-[10px] font-extrabold uppercase ${style}`}
                  >
                    {promise.status}
                  </span>
                </div>

                <div className="flex flex-wrap items-center gap-2 border-t border-slate-800/60 pt-1.5">
                  <span className="inline-flex items-center gap-1 rounded bg-amber-500/10 px-2 py-0.5 font-mono text-[10px] font-bold text-amber-300">
                    <span>Confidence: {(promise.confidence * 100).toFixed(0)}%</span>
                    <span className="text-slate-500">|</span>
                    <span className="text-slate-400">Threshold: 70%</span>
                  </span>
                  <span className="rounded bg-slate-800 px-2 py-0.5 font-mono text-[10px] text-slate-400">
                    {promise.resolved_at
                      ? `resolved ${formatTimestamp(promise.resolved_at)}`
                      : "awaiting grace window"}
                  </span>
                </div>
              </li>
            );
          })}
        </ol>
      )}
    </section>
  );
}

export default PromiseList;
