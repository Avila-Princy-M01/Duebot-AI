import type { AuditRow, InteractionRow } from "../../lib/types";

interface InvoiceTimelineProps {
  interactions: InteractionRow[];
  audit: AuditRow[];
}

export function InvoiceTimeline({ interactions, audit }: InvoiceTimelineProps) {
  return (
    <div className="grid gap-6 md:grid-cols-2">
      {/* Communication Log */}
      <section className="rounded-2xl border border-slate-800/80 bg-panel/70 p-5 backdrop-blur-md shadow-lg space-y-3">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <h3 className="text-sm font-bold text-white flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-sky-400" />
            Communication Log ({interactions.length})
          </h3>
          <span className="text-[11px] font-mono text-slate-500">WhatsApp Channel</span>
        </div>

        {interactions.length === 0 ? (
          <p className="text-xs text-slate-500 py-4 text-center">No messages sent or received yet.</p>
        ) : (
          <ol className="space-y-3">
            {interactions.map((item) => {
              const isOutbound = item.direction === "outbound";
              return (
                <li
                  key={item.id}
                  className={`rounded-xl border ${
                    isOutbound ? "border-slate-800 bg-slate-900/90" : "border-indigo-500/30 bg-indigo-950/20"
                  } p-3.5 space-y-2`}
                >
                  <div className="flex flex-wrap items-center justify-between gap-1 text-[11px]">
                    <div className="flex items-center gap-2">
                      <span
                        className={`rounded-full border px-2 py-0.5 text-[10px] font-extrabold uppercase ${
                          isOutbound
                            ? "bg-sky-500/10 text-sky-400 border-sky-500/30"
                            : "bg-purple-500/10 text-purple-400 border-purple-500/30"
                        }`}
                      >
                        {item.direction}
                      </span>
                      {item.intent_label ? (
                        <span className="rounded bg-slate-800 px-1.5 py-0.5 font-mono text-[10px] text-amber-300">
                          intent: {item.intent_label}
                        </span>
                      ) : null}
                    </div>

                    {item.confidence !== null && item.confidence !== undefined ? (
                      <span className="rounded bg-indigo-900/60 border border-indigo-500/40 px-2 py-0.5 font-mono text-[10px] font-bold text-indigo-300">
                        conf: {(Number(item.confidence) * 100).toFixed(0)}%
                      </span>
                    ) : null}
                  </div>

                  <p className="whitespace-pre-wrap font-mono text-xs text-slate-200 leading-relaxed bg-slate-950/60 p-2.5 rounded-lg border border-slate-800/60">
                    {item.message_text}
                  </p>

                  <p className="text-[10px] font-mono text-slate-500 text-right">
                    {item.sent_at}
                  </p>
                </li>
              );
            })}
          </ol>
        )}
      </section>

      {/* Append-Only State Machine Audit */}
      <section className="rounded-2xl border border-slate-800/80 bg-panel/70 p-5 backdrop-blur-md shadow-lg space-y-3">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <h3 className="text-sm font-bold text-white flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-emerald-400" />
            Append-Only Audit Log ({audit.length})
          </h3>
          <span className="text-[11px] font-mono text-slate-500">Deterministic Engine</span>
        </div>

        {audit.length === 0 ? (
          <p className="text-xs text-slate-500 py-4 text-center">No state transitions recorded yet.</p>
        ) : (
          <ol className="space-y-3">
            {audit.map((item) => {
              const meta = item.extra_metadata as Record<string, unknown> | null;
              const confidence = meta?.confidence as number | undefined;
              const intent = meta?.intent as string | undefined;

              return (
                <li
                  key={item.id}
                  className="rounded-xl border border-slate-800/80 bg-slate-900/80 p-3.5 space-y-2 hover:border-slate-700 transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-1.5 font-mono text-xs">
                      <span className="rounded bg-slate-800 px-2 py-0.5 text-slate-400 uppercase font-bold text-[10px]">
                        {item.from_state}
                      </span>
                      <span className="text-sky-400 font-bold">→</span>
                      <span className="rounded bg-sky-500/20 border border-sky-500/30 px-2 py-0.5 text-sky-300 uppercase font-bold text-[10px]">
                        {item.to_state}
                      </span>
                    </div>

                    <span className="rounded bg-slate-800/80 px-2 py-0.5 text-[10px] font-bold uppercase text-slate-400">
                      actor: {item.actor}
                    </span>
                  </div>

                  <p className="text-xs text-slate-300 leading-relaxed font-medium">
                    {item.reasoning_summary}
                  </p>

                  {/* Confidence & Policy Badges */}
                  {(confidence !== undefined && confidence !== null) || intent ? (
                    <div className="flex flex-wrap items-center gap-2 pt-1 border-t border-slate-800/60 text-[11px]">
                      {confidence !== undefined && confidence !== null ? (
                        <div className="inline-flex items-center gap-1 rounded bg-amber-500/10 border border-amber-500/30 px-2 py-0.5 font-mono text-[10px] font-bold text-amber-300">
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
                        </div>
                      ) : null}

                      {intent ? (
                        <span className="rounded bg-slate-800 px-2 py-0.5 font-mono text-[10px] text-slate-300">
                          classified_intent: {intent}
                        </span>
                      ) : null}
                    </div>
                  ) : null}

                  <p className="text-[10px] font-mono text-slate-500 text-right">
                    {item.occurred_at}
                  </p>
                </li>
              );
            })}
          </ol>
        )}
      </section>
    </div>
  );
}

export default InvoiceTimeline;
