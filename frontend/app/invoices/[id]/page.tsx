"use client";

import { useEffect, useState } from "react";
import { notFound } from "next/navigation";
import { EdgeCaseBadge, edgeCaseMeta } from "../../../components/invoices/EdgeCaseBadge";
import { InvoiceTimeline } from "../../../components/invoices/InvoiceTimeline";
import { PromiseList } from "../../../components/invoices/PromiseList";
import { getInvoice, injectReply, previewNudge, resolveInvoice, triggerNudge } from "../../../lib/api";
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
  const [resolveReasoning, setResolveReasoning] = useState("");
  const [resolveError, setResolveError] = useState<string | null>(null);
  const [resolving, setResolving] = useState(false);
  const [resolveSuccess, setResolveSuccess] = useState<string | null>(null);

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
      {/* Header Banner */}
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between rounded-2xl border border-slate-800/80 bg-panel/70 p-6 backdrop-blur-md">
        <div className="space-y-1.5">
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-2xl font-extrabold text-white">{invoice.invoice_number}</h1>
            <EdgeCaseBadge edgeCase={invoice.edge_case} />
          </div>
          <p className="text-sm font-semibold text-slate-200">
            <a href={`/buyers/${invoice.buyer_id}`} className="hover:underline text-sky-400">
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
              Buyer Profile & Open Invoices →
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

      {/* Human Review Resolution Panel — ELEVATED TO TOP for immediate operator visibility */}
      {invoice.state === "human_review" && (
        <div className="rounded-2xl border border-amber-500/40 bg-amber-950/20 p-6 backdrop-blur-md space-y-4 shadow-lg shadow-amber-500/5">
          <div className="flex items-start gap-3">
            <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-amber-500/20 text-amber-400 text-base font-extrabold border border-amber-500/30">!</span>
            <div>
              <h3 className="text-sm font-extrabold text-amber-300">Human Review Required (Parked State)</h3>
              <p className="mt-0.5 text-xs leading-relaxed text-slate-300">
                This invoice has been safety-routed to the human queue (ambiguous reply below 70% confidence threshold, active dispute, or contact cap reached). As the merchant operator, review and record your decision below.
              </p>
            </div>
          </div>

          <div>
            <label
              htmlFor="resolution-reasoning"
              className="mb-1.5 block text-xs font-bold uppercase tracking-wider text-slate-300"
            >
              Operator Reasoning <span className="text-rose-400">*</span>
            </label>
            <textarea
              id="resolution-reasoning"
              className="w-full rounded-xl border border-amber-500/30 bg-slate-900 p-3 text-xs text-white placeholder-slate-500 focus:border-amber-400 focus:outline-none leading-relaxed"
              placeholder="e.g. Spoke with buyer directly on phone — confirmed bank transfer is processing. Marking as recovered."
              value={resolveReasoning}
              onChange={(e) => { setResolveReasoning(e.target.value); setResolveError(null); }}
              rows={2}
              aria-label="Resolution reasoning"
            />
            {resolveError && (
              <p className="mt-1 text-xs font-semibold text-rose-400" role="alert">{resolveError}</p>
            )}
          </div>

          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              disabled={resolving}
              className="rounded-xl bg-gradient-to-r from-emerald-500 to-teal-600 px-4 py-2.5 text-xs font-bold text-white shadow-lg shadow-emerald-500/20 hover:brightness-110 disabled:opacity-50 transition-all flex items-center gap-1.5"
              onClick={() => {
                if (resolveReasoning.trim().length < 5) { setResolveError("Reasoning must be at least 5 characters."); return; }
                setResolving(true);
                void resolveInvoice(invoice.invoice_id, "recovered", resolveReasoning.trim())
                  .then(async () => {
                    const fresh = await getInvoice(params.id);
                    setInvoice(fresh.data);
                    setResolveReasoning("");
                    setResolveSuccess("Marked as recovered — invoice is now settled.");
                  })
                  .catch((err: unknown) => setResolveError(err instanceof Error ? err.message : "Failed to resolve"))
                  .finally(() => setResolving(false));
              }}
            >
              <span>✓ Mark Recovered</span>
            </button>
            <button
              type="button"
              disabled={resolving}
              className="rounded-xl border border-rose-500/40 bg-rose-950/30 px-4 py-2.5 text-xs font-bold text-rose-300 hover:bg-rose-900/40 disabled:opacity-50 transition-all flex items-center gap-1.5"
              onClick={() => {
                if (resolveReasoning.trim().length < 5) { setResolveError("Reasoning must be at least 5 characters."); return; }
                setResolving(true);
                void resolveInvoice(invoice.invoice_id, "closed", resolveReasoning.trim())
                  .then(async () => {
                    const fresh = await getInvoice(params.id);
                    setInvoice(fresh.data);
                    setResolveReasoning("");
                    setResolveSuccess("Invoice closed — workflow terminated.");
                  })
                  .catch((err: unknown) => setResolveError(err instanceof Error ? err.message : "Failed to resolve"))
                  .finally(() => setResolving(false));
              }}
            >
              <span>✕ Close / Write Off</span>
            </button>
          </div>
          {resolveSuccess && (
            <p className="text-xs font-semibold text-emerald-400" role="status">{resolveSuccess}</p>
          )}
        </div>
      )}

      {invoice.edge_case && invoice.edge_case !== "none" ? (
        <div className="rounded-2xl border border-violet-500/25 bg-violet-950/20 p-4">
          <p className="text-xs font-extrabold uppercase tracking-wider text-violet-300">
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
                <dd className="font-mono text-xs text-sky-400">{invoice.payment_link_id}</dd>
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

      {/* Action Buttons with clear Visual Hierarchy */}
      <div className="flex flex-wrap items-center gap-3">
        {/* Primary Action Button */}
        <button
          type="button"
          className="rounded-xl bg-gradient-to-r from-emerald-500 to-teal-600 px-5 py-2.5 text-xs font-extrabold text-white shadow-lg shadow-emerald-500/25 ring-1 ring-emerald-400/40 hover:brightness-110 transition-all flex items-center gap-2"
          onClick={() => {
            void triggerNudge(invoice.invoice_id, false).then(async () => {
              const fresh = await getInvoice(params.id);
              setInvoice(fresh.data);
            });
          }}
        >
          <svg className="h-4 w-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
          </svg>
          <span>Send WhatsApp Nudge</span>
        </button>

        {/* Secondary Action Button */}
        <button
          type="button"
          className="rounded-xl border border-slate-700 bg-slate-800/80 px-4 py-2.5 text-xs font-bold text-slate-200 hover:bg-slate-700 hover:text-white transition-all flex items-center gap-1.5"
          onClick={() => {
            void previewNudge(invoice.invoice_id).then((res) => setPreview(res.data));
          }}
        >
          <svg className="h-4 w-4 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
          </svg>
          <span>Preview Nudge</span>
        </button>

        {/* Tertiary Action Button */}
        <button
          type="button"
          className="rounded-xl border border-sky-500/30 bg-sky-500/10 px-4 py-2.5 text-xs font-bold text-sky-400 hover:bg-sky-500/20 transition-all flex items-center gap-1.5"
          onClick={() => {
            void triggerNudge(invoice.invoice_id, true).then((res) => setPreview(res.data.preview));
          }}
        >
          <span>Dry-Run Trigger</span>
        </button>
      </div>

      {preview ? (
        <div className="rounded-2xl border border-emerald-500/30 bg-emerald-950/20 p-5 text-xs">
          <p className="text-slate-300 font-semibold mb-2">{preview.policy_reason}</p>
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
          aria-label="Buyer simulated WhatsApp reply"
        />
        <button
          type="button"
          className="rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-2 text-xs font-bold text-amber-300 hover:bg-amber-500 hover:text-white transition-all"
          onClick={() => {
            void injectReply(invoice.invoice_id, reply).then(async () => {
              const fresh = await getInvoice(params.id);
              setInvoice(fresh.data);
            });
          }}
        >
          Inject WhatsApp Reply
        </button>
      </div>

      <PromiseList promises={invoice.promises} promiseOutcome={invoice.promise_outcome} />
      <InvoiceTimeline interactions={invoice.interactions} audit={invoice.audit} />
    </div>
  );
}
