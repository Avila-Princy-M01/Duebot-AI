"use client";

import { useEffect, useState } from "react";
import { notFound } from "next/navigation";
import { EdgeCaseBadge, edgeCaseMeta } from "../../../components/invoices/EdgeCaseBadge";
import { InvoiceTimeline } from "../../../components/invoices/InvoiceTimeline";
import { PromiseList } from "../../../components/invoices/PromiseList";
import { getInvoice, injectReply, previewNudge, triggerNudge } from "../../../lib/api";
import { formatDate, formatINR } from "../../../lib/format";
import type { InvoiceDetail, NudgePreview } from "../../../lib/types";

interface InvoiceDetailPageProps {
  params: { id: string };
}

export default function InvoiceDetailPage({ params }: InvoiceDetailPageProps) {
  const [invoice, setInvoice] = useState<InvoiceDetail | null>(null);
  const [preview, setPreview] = useState<NudgePreview | null>(null);
  const [reply, setReply] = useState("will sort it out soon");
  const [isNotFound, setIsNotFound] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void getInvoice(params.id)
      .then((res) => {
        if (!res?.data) {
          setIsNotFound(true);
        } else {
          setInvoice(res.data);
        }
      })
      .catch((err: unknown) => {
        const msg = err instanceof Error ? err.message : "";
        if (msg.includes("404") || msg.toLowerCase().includes("not found")) {
          setIsNotFound(true);
        } else {
          setError(msg || "Failed to load invoice");
        }
      });
  }, [params.id]);

  if (isNotFound) {
    notFound();
  }
  if (error) return <div className="rounded-xl border border-rose-500/30 bg-rose-950/30 p-4 text-xs text-rose-300" role="alert">{error}</div>;
  if (!invoice) return <div className="p-8 text-center text-xs text-slate-500" aria-busy="true">Loading invoice details...</div>;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between rounded-2xl border border-slate-800/80 bg-panel/70 p-6 backdrop-blur-md">
        <div className="space-y-1.5">
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-2xl font-extrabold text-white">{invoice.invoice_number}</h1>
            <EdgeCaseBadge edgeCase={invoice.edge_case} />
          </div>
          <p className="text-sm font-semibold text-slate-200">
            <a href={`/buyers/${invoice.buyer_id}`} className="hover:underline">
              {invoice.buyer_company_name}
            </a>
            <span className="mx-1.5 text-slate-600">|</span>
            <span className="text-xs font-medium text-slate-400">{invoice.buyer_contact_name}</span>
          </p>
          <p className="text-xs text-slate-400">
            State: <span className="font-bold text-sky-400">{invoice.state.replace(/_/g, " ")}</span>{" "}
            | Risk: <span className="font-bold text-amber-400">{invoice.risk_tier}</span> |{" "}
            {Number(invoice.outstanding_amount) === 0 && invoice.paid_date ? (
              <span className="font-bold text-emerald-400">
                Paid {formatDate(invoice.paid_date)}
                {invoice.days_late > 0 ? ` (${invoice.days_late}d late)` : " (on time)"}
              </span>
            ) : invoice.days_overdue > 0 ? (
              <span className="font-bold text-rose-400">{invoice.days_overdue} days overdue</span>
            ) : (
              <span className="text-slate-400">Not yet due</span>
            )}{" "}
            |{" "}
            <a href={`/buyers/${invoice.buyer_id}`} className="font-semibold text-sky-400 hover:underline">
              Buyer Brief
            </a>
          </p>
        </div>
        <div className="text-right">
          <div className="font-mono text-2xl font-extrabold text-white">
            {formatINR(invoice.total_amount)}
          </div>
          {Number(invoice.outstanding_amount) > 0 ? (
            <div className="mt-0.5 font-mono text-xs font-bold text-amber-300">
              {formatINR(invoice.outstanding_amount)} outstanding
            </div>
          ) : (
            <div className="mt-0.5 text-xs font-bold uppercase text-emerald-400">Settled</div>
          )}
        </div>
      </div>

      {invoice.edge_case && invoice.edge_case !== "none" ? (
        <div className="rounded-2xl border border-violet-500/25 bg-violet-950/20 p-4">
          <p className="text-[11px] font-extrabold uppercase tracking-wider text-violet-300">
            Edge case under test: {edgeCaseMeta(invoice.edge_case).label}
          </p>
          <p className="mt-1 text-xs leading-relaxed text-slate-300">
            {edgeCaseMeta(invoice.edge_case).title}
          </p>
        </div>
      ) : null}

      <div className="grid gap-4 md:grid-cols-2">
        <section className="rounded-2xl border border-slate-800/80 bg-panel/70 p-5 backdrop-blur-md">
          <h3 className="mb-3 border-b border-slate-800 pb-2 text-sm font-bold text-white">
            Amount Breakdown
          </h3>
          <dl className="space-y-2 text-xs">
            <div className="flex justify-between">
              <dt className="text-slate-400">Subtotal</dt>
              <dd className="font-mono text-slate-200">{formatINR(invoice.subtotal_amount)}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-slate-400">GST @ {invoice.gst_rate}%</dt>
              <dd className="font-mono text-slate-200">{formatINR(invoice.gst_amount)}</dd>
            </div>
            <div className="flex justify-between border-t border-slate-800 pt-2">
              <dt className="font-bold text-white">Invoice Total</dt>
              <dd className="font-mono font-bold text-white">{formatINR(invoice.total_amount)}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-slate-400">Received</dt>
              <dd className="font-mono text-emerald-400">{formatINR(invoice.amount_paid)}</dd>
            </div>
            <div className="flex justify-between border-t border-slate-800 pt-2">
              <dt className="font-bold text-amber-300">Outstanding</dt>
              <dd className="font-mono font-bold text-amber-300">
                {formatINR(invoice.outstanding_amount)}
              </dd>
            </div>
          </dl>
        </section>

        <section className="rounded-2xl border border-slate-800/80 bg-panel/70 p-5 backdrop-blur-md">
          <h3 className="mb-3 border-b border-slate-800 pb-2 text-sm font-bold text-white">
            Terms and Dates
          </h3>
          <dl className="space-y-2 text-xs">
            <div className="flex justify-between">
              <dt className="text-slate-400">Issued</dt>
              <dd className="text-slate-200">{formatDate(invoice.issue_date)}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-slate-400">Due</dt>
              <dd className="font-semibold text-slate-200">{formatDate(invoice.due_date)}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-slate-400">Payment terms</dt>
              <dd className="text-slate-200">Net {invoice.payment_terms_days} days</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-slate-400">Paid</dt>
              <dd className="text-slate-200">
                {invoice.paid_date ? formatDate(invoice.paid_date) : "Not paid"}
              </dd>
            </div>
            <div className="flex justify-between border-t border-slate-800 pt-2">
              <dt className="text-slate-400">Buyer reliability</dt>
              <dd className="text-slate-200">
                {invoice.buyer_reliability_tier.replace(/_/g, " ")}{" "}
                <span className="text-slate-400">
                  ({(invoice.buyer_on_time_payment_rate * 100).toFixed(0)}% on time)
                </span>
              </dd>
            </div>
            {invoice.payment_link_id ? (
              <div className="flex justify-between">
                <dt className="text-slate-400">Razorpay link</dt>
                <dd className="font-mono text-[10px] text-sky-400">{invoice.payment_link_id}</dd>
              </div>
            ) : null}
          </dl>
        </section>
      </div>

      {invoice.notes ? (
        <div className="rounded-2xl border border-slate-800/80 bg-panel/70 p-4 text-xs text-slate-300">
          <span className="font-bold text-slate-400">Note: </span>
          {invoice.notes}
        </div>
      ) : null}

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

      <PromiseList promises={invoice.promises} promiseOutcome={invoice.promise_outcome} />

      <InvoiceTimeline interactions={invoice.interactions} audit={invoice.audit} />
    </div>
  );
}
