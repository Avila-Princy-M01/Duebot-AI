"use client";

import { useEffect, useState } from "react";
import { listInbox } from "../../lib/api";
import type { InboxRow } from "../../lib/types";

export function InboxPage() {
  const [rows, setRows] = useState<InboxRow[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void listInbox()
      .then((res) => setRows(res.data))
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "failed"));
  }, []);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Simulated WhatsApp inbox</h1>
      <p className="text-sm text-slate-400">
        Demo channel. Sends are logged here after policy allows them. Inbound replies are injected
        from the invoice page.
      </p>
      {error ? <p className="text-red-300">{error}</p> : null}
      <ol className="space-y-3">
        {rows.map((row) => (
          <li key={row.interaction_id} className="rounded-xl border border-slate-800 bg-panel p-4">
            <p className="text-xs text-slate-500">
              {row.direction} · {row.invoice_id} · {row.to_phone_masked}
            </p>
            <p className="mt-2 whitespace-pre-wrap text-sm">{row.body}</p>
          </li>
        ))}
      </ol>
    </div>
  );
}

export default InboxPage;
