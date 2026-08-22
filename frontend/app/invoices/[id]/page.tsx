"use client";

import { useEffect, useState } from "react";
import { InvoiceTimeline } from "../../../components/invoices/InvoiceTimeline";
import { getInvoice, injectReply, previewNudge, triggerNudge } from "../../../lib/api";
import type { InvoiceDetail, NudgePreview } from "../../../lib/types";

interface InvoiceDetailPageProps {
  params: { id: string };
}

export function InvoiceDetailPage({ params }: InvoiceDetailPageProps) {
  const [invoice, setInvoice] = useState<InvoiceDetail | null>(null);
  const [preview, setPreview] = useState<NudgePreview | null>(null);
  const [reply, setReply] = useState("will sort it out soon");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void getInvoice(params.id)
      .then((res) => setInvoice(res.data))
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "load failed"));
  }, [params.id]);

  if (error) return <p className="text-red-300">{error}</p>;
  if (!invoice) return <p className="text-slate-400">Loading…</p>;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">{invoice.invoice_number}</h1>
        <p className="text-sm text-slate-400">
          state={invoice.state} · risk={invoice.risk_tier} · {invoice.days_overdue} days overdue
        </p>
      </div>
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          className="rounded-md bg-slate-700 px-3 py-1.5 text-sm"
          onClick={() => {
            void previewNudge(invoice.invoice_id).then((res) => setPreview(res.data));
          }}
        >
          Preview nudge
        </button>
        <button
          type="button"
          className="rounded-md bg-sky-600 px-3 py-1.5 text-sm"
          onClick={() => {
            void triggerNudge(invoice.invoice_id, true).then((res) => setPreview(res.data.preview));
          }}
        >
          Dry-run trigger
        </button>
        <button
          type="button"
          className="rounded-md bg-emerald-600 px-3 py-1.5 text-sm"
          onClick={() => {
            void triggerNudge(invoice.invoice_id, false).then(async () => {
              const fresh = await getInvoice(params.id);
              setInvoice(fresh.data);
            });
          }}
        >
          Send nudge
        </button>
      </div>
      {preview ? (
        <div className="rounded-xl border border-slate-800 bg-panel p-4 text-sm">
          <p className="text-slate-400">{preview.policy_reason}</p>
          <p className="mt-2 whitespace-pre-wrap">{preview.drafted_message}</p>
        </div>
      ) : null}
      <div className="rounded-xl border border-slate-800 bg-panel p-4">
        <p className="text-sm font-medium">Simulate buyer reply</p>
        <textarea
          className="mt-2 w-full rounded-md bg-ink p-2 text-sm"
          value={reply}
          onChange={(event) => setReply(event.target.value)}
          rows={3}
        />
        <button
          type="button"
          className="mt-2 rounded-md bg-amber-500 px-3 py-1.5 text-sm text-ink"
          onClick={() => {
            void injectReply(invoice.invoice_id, reply).then(async () => {
              const fresh = await getInvoice(params.id);
              setInvoice(fresh.data);
            });
          }}
        >
          Submit reply
        </button>
      </div>
      <InvoiceTimeline interactions={invoice.interactions} audit={invoice.audit} />
    </div>
  );
}

export default InvoiceDetailPage;
