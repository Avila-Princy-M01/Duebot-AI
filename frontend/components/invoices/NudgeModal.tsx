"use client";

import { useEffect, useState } from "react";
import { previewNudge, triggerNudge } from "../../lib/api";
import type { NudgePreview } from "../../lib/types";

interface NudgeModalProps {
  invoiceId: string | null;
  onClose: () => void;
  onSuccess?: () => void;
}

export function NudgeModal({ invoiceId, onClose, onSuccess }: NudgeModalProps) {
  const [loading, setLoading] = useState(true);
  const [preview, setPreview] = useState<NudgePreview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const [dryRun, setDryRun] = useState(false);
  const [statusMsg, setStatusMsg] = useState<string | null>(null);

  useEffect(() => {
    if (!invoiceId) return;
    setLoading(true);
    setError(null);
    setStatusMsg(null);
    previewNudge(invoiceId)
      .then((res) => {
        setPreview(res.data);
        setLoading(false);
      })
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : "Failed to load preview");
        setLoading(false);
      });
  }, [invoiceId]);

  if (!invoiceId) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm animate-in fade-in duration-200" role="dialog" aria-modal="true" aria-labelledby="nudge-modal-title">
      <div className="w-full max-w-lg rounded-2xl border border-slate-700/80 bg-panel p-6 shadow-2xl shadow-sky-950/50">
        <div className="flex items-center justify-between border-b border-slate-800 pb-4">
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-sky-500/10 text-sky-400 border border-sky-500/20">
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
              </svg>
            </div>
            <div>
              <h3 id="nudge-modal-title" className="text-base font-bold text-white">WhatsApp Nudge Preview</h3>
              <p className="text-xs text-slate-400">Invoice #{invoiceId}</p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close modal"
            className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white"
          >
            ✕
          </button>
        </div>

        <div className="py-4">
          {loading ? (
            <div className="flex flex-col items-center justify-center py-8 gap-3 text-slate-400">
              <svg className="h-6 w-6 animate-spin text-sky-400" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
              <span className="text-xs">Generating WhatsApp template...</span>
            </div>
          ) : error ? (
            <div className="rounded-xl border border-rose-500/30 bg-rose-950/30 p-4 text-xs text-rose-300">
              {error}
            </div>
          ) : preview ? (
            <div className="space-y-4">
              <div className="rounded-xl border border-emerald-500/30 bg-emerald-950/20 p-4 text-xs">
                <div className="flex items-center justify-between text-slate-400 mb-2">
                  <span className="font-semibold text-emerald-400">Target Invoice: {preview.invoice_id}</span>
                  <span className="rounded bg-slate-800 px-2 py-0.5 text-[10px] uppercase">{preview.channel}</span>
                </div>
                <div className="rounded-lg border border-emerald-500/20 bg-slate-900/90 p-3 font-mono text-[13px] leading-relaxed text-slate-200 shadow-inner">
                  {preview.drafted_message}
                </div>
              </div>

              <div className="flex items-center justify-between pt-2">
                <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={dryRun}
                    onChange={(e) => setDryRun(e.target.checked)}
                    className="rounded border-slate-700 bg-slate-900 text-sky-500 focus:ring-sky-500"
                  />
                  <span>Dry Run Mode (Simulate without sending)</span>
                </label>
              </div>

              {statusMsg ? (
                <div className="rounded-lg border border-sky-500/30 bg-sky-950/40 p-3 text-xs text-sky-300">
                  {statusMsg}
                </div>
              ) : null}
            </div>
          ) : null}
        </div>

        <div className="flex items-center justify-end gap-3 border-t border-slate-800 pt-4">
          <button
            type="button"
            onClick={onClose}
            className="rounded-xl border border-slate-800 px-4 py-2 text-xs font-semibold text-slate-400 hover:bg-slate-800 hover:text-white"
          >
            Cancel
          </button>
          <button
            type="button"
            disabled={loading || sending || !preview}
            onClick={() => {
              setSending(true);
              setStatusMsg(null);
              triggerNudge(invoiceId, dryRun)
                .then((res) => {
                  setStatusMsg(
                    res.data.sent
                      ? `WhatsApp Nudge Sent! New state: ${res.data.new_state}`
                      : `Dry-run completed. State: ${res.data.new_state}`
                  );
                  setSending(false);
                  if (onSuccess) onSuccess();
                })
                .catch((err: unknown) => {
                  setStatusMsg(err instanceof Error ? err.message : "Trigger failed");
                  setSending(false);
                });
            }}
            className="flex items-center gap-2 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-600 px-5 py-2 text-xs font-bold text-white shadow-lg shadow-emerald-500/25 transition-all hover:scale-[1.02] disabled:opacity-50"
          >
            {sending ? (
              <svg className="h-3.5 w-3.5 animate-spin text-white" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
            ) : (
              <svg className="h-3.5 w-3.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
              </svg>
            )}
            <span>{sending ? "Sending..." : dryRun ? "Simulate Trigger" : "Send WhatsApp Nudge"}</span>
          </button>
        </div>
      </div>
    </div>
  );
}

export default NudgeModal;
