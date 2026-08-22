"use client";

import { useEffect, useState } from "react";
import { InvoiceTimeline } from "../../../components/invoices/InvoiceTimeline";
import { getInvoice, injectReply, previewNudge, triggerNudge } from "../../../lib/api";
import type { InvoiceDetail, NudgePreview } from "../../../lib/types";

interface InvoiceDetailPageProps {
  params: { id: string };
}

export default function InvoiceDetailPage({ params }: InvoiceDetailPageProps) {
  const [invoice, setInvoice] = useState<InvoiceDetail | null>(null);
  const [preview, setPreview] = useState<NudgePreview | null>(null);
  const [reply, setReply] = useState("will sort it out soon");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void getInvoice(params.id)
      .then((res) => setInvoice(res.data))
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "load failed"));
  }, [params.id]);

  if (error) return <div className="rounded-xl border border-rose-500/30 bg-rose-950/30 p-4 text-xs text-rose-300">{error}</div>;
  if (!invoice) return <div className="p-8 text-center text-xs text-slate-500">Loading invoice details...</div>;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between rounded-2xl border border-slate-800/80 bg-panel/70 p-6 backdrop-blur-md">
        <div>
          <h1 className="text-2xl font-extrabold text-white">{invoice.invoice_number}</h1>
          <p className="mt-1 text-xs text-slate-400">
            State: <span className="font-bold text-sky-400">{invoice.state}</span> · Risk: <span className="font-bold text-amber-400">{invoice.risk_tier}</span> · {invoice.days_overdue} days overdue
          </p>
        </div>
        <div className="font-mono text-2xl font-extrabold text-white">
          ₹{Number(invoice.total_amount).toLocaleString("en-IN")}
        </div>
      </div>

      <div className="flex flex-wrap gap-3">
        <button
          type="button"
          className="rounded-xl border border-slate-800 bg-panel px-4 py-2 text-xs font-bold text-slate-300 hover:bg-slate-800"
          onClick={() => {
            void previewNudge(invoice.invoice_id).then((res) => setPreview(res.data));
          }}
        >
          Preview Nudge
        </button>
        <button
          type="button"
          className="rounded-xl border border-sky-500/30 bg-sky-500/10 px-4 py-2 text-xs font-bold text-sky-400 hover:bg-sky-500 hover:text-white"
          onClick={() => {
            void triggerNudge(invoice.invoice_id, true).then((res) => setPreview(res.data.preview));
          }}
        >
          Dry-Run Trigger
        </button>
        <button
          type="button"
          className="rounded-xl bg-gradient-to-r from-emerald-500 to-teal-600 px-4 py-2 text-xs font-bold text-white shadow-lg shadow-emerald-500/20"
          onClick={() => {
            void triggerNudge(invoice.invoice_id, false).then(async () => {
              const fresh = await getInvoice(params.id);
              setInvoice(fresh.data);
            });
          }}
        >
          Send WhatsApp Nudge
        </button>
      </div>

      {preview ? (
        <div className="rounded-2xl border border-emerald-500/30 bg-emerald-950/20 p-5 text-xs">
          <p className="text-slate-400 font-semibold mb-2">{preview.policy_reason}</p>
          <div className="rounded-xl border border-emerald-500/20 bg-slate-900/90 p-4 font-mono text-slate-200 leading-relaxed shadow-inner">
            {preview.drafted_message}
          </div>
        </div>
      ) : null}

      <div className="rounded-2xl border border-slate-800/80 bg-panel/70 p-6 backdrop-blur-md space-y-3">
        <h3 className="text-sm font-bold text-white">Simulate Buyer WhatsApp Reply</h3>
        <textarea
          className="w-full rounded-xl border border-slate-800 bg-slate-900 p-3 text-xs text-white placeholder-slate-500 focus:border-amber-500 focus:outline-none"
          value={reply}
          onChange={(event) => setReply(event.target.value)}
          rows={3}
        />
        <button
          type="button"
          className="rounded-xl bg-gradient-to-r from-amber-500 to-orange-600 px-4 py-2 text-xs font-bold text-slate-950 shadow-lg shadow-amber-500/20"
          onClick={() => {
            void injectReply(invoice.invoice_id, reply).then(async () => {
              const fresh = await getInvoice(params.id);
              setInvoice(fresh.data);
            });
          }}
        >
          Submit Reply →
        </button>
      </div>

      <InvoiceTimeline interactions={invoice.interactions} audit={invoice.audit} />
    </div>
  );
}
