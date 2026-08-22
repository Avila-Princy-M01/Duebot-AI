import type { AuditRow, InteractionRow } from "../../lib/types";

interface InvoiceTimelineProps {
  interactions: InteractionRow[];
  audit: AuditRow[];
}

export function InvoiceTimeline({ interactions, audit }: InvoiceTimelineProps) {
  return (
    <div className="grid gap-6 md:grid-cols-2">
      <section>
        <h3 className="mb-3 text-sm font-semibold text-slate-300">Messages</h3>
        <ol className="space-y-3">
          {interactions.map((item) => (
            <li key={item.id} className="rounded-lg border border-slate-800 bg-panel p-3 text-sm">
              <p className="text-xs text-slate-500">
                {item.direction} · {item.intent_label} · {item.sent_at}
              </p>
              <p className="mt-1 whitespace-pre-wrap text-slate-100">{item.message_text}</p>
            </li>
          ))}
        </ol>
      </section>
      <section>
        <h3 className="mb-3 text-sm font-semibold text-slate-300">Audit</h3>
        <ol className="space-y-3">
          {audit.map((item) => (
            <li key={item.id} className="rounded-lg border border-slate-800 bg-panel p-3 text-sm">
              <p className="font-mono text-xs text-sky-300">
                {item.from_state} → {item.to_state}
              </p>
              <p className="mt-1 text-slate-200">{item.reasoning_summary}</p>
              <p className="mt-1 text-xs text-slate-500">
                {item.actor} · {item.occurred_at}
              </p>
            </li>
          ))}
        </ol>
      </section>
    </div>
  );
}
