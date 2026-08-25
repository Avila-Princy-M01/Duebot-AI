"use client";

import { useEffect, useState } from "react";
import { injectReply, listInvoices } from "../../lib/api";

interface ReplySimulatorProps {
  onReplyInjected?: () => void;
}

const PRESETS = [
  { text: "Paisa transfer ho jayega Friday tak", label: "Promise (Hinglish)" },
  { text: "Bill total is wrong, rate was 450", label: "Dispute Rate" },
  { text: "Stop sending messages to my WhatsApp number", label: "Opt-Out" },
  { text: "Require physical invoice copy for audit first", label: "Objection" },
];

export function ReplySimulator({ onReplyInjected }: ReplySimulatorProps) {
  const [invoiceId, setInvoiceId] = useState("INV-2026-001");
  const [replyText, setReplyText] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<string | null>(null);

  useEffect(() => {
    void listInvoices({ limit: 1 } as any)
      .then((res) => {
        const first = res.data?.[0];
        if (first?.invoice_id) {
          setInvoiceId(first.invoice_id);
        }
      })
      .catch(() => {});
  }, []);

  const handleInject = async () => {
    if (!invoiceId.trim() || !replyText.trim()) return;
    setBusy(true);
    setResult(null);
    try {
      const res = await injectReply(invoiceId.trim(), replyText.trim());
      const note = (res.data as Record<string, string>).note;
      if (note) {
        setResult(note);
      } else {
        setResult(`Reply processed successfully! New Invoice State: ${res.data.state}`);
      }
      setReplyText("");
      if (onReplyInjected) onReplyInjected();
    } catch (err: unknown) {
      setResult(err instanceof Error ? err.message : "Failed to process reply");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="glass-panel rounded-3xl p-6 sm:p-8 space-y-5">
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-indigo-500/15 text-indigo-400 border border-indigo-400/30 shadow-md shadow-indigo-500/10">
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
          </svg>
        </div>
        <div>
          <h3 className="text-base font-extrabold text-white">Live WhatsApp Reply Test Bench</h3>
          <p className="text-xs text-slate-300">Simulate incoming buyer WhatsApp replies to evaluate zero-shot intent classification & state safety transitions.</p>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <div>
          <label htmlFor="target-invoice-id-input" className="block text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-1.5">
            Target Invoice ID
          </label>
          <input
            id="target-invoice-id-input"
            type="text"
            value={invoiceId}
            onChange={(e) => setInvoiceId(e.target.value)}
            aria-label="Target Invoice ID"
            className="glass-input w-full rounded-2xl px-3.5 py-2.5 text-xs font-mono text-white focus:outline-none"
          />
        </div>

        <div className="md:col-span-2">
          <label htmlFor="incoming-reply-text-input" className="block text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-1.5">
            Incoming Buyer WhatsApp Reply Text
          </label>
          <div className="flex gap-2">
            <input
              id="incoming-reply-text-input"
              type="text"
              placeholder="e.g. Paisa Friday tak bhej dunga..."
              value={replyText}
              onChange={(e) => setReplyText(e.target.value)}
              aria-label="Incoming Buyer WhatsApp Reply Text"
              className="glass-input flex-1 rounded-2xl px-4 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none"
            />
            <button
              type="button"
              disabled={busy || !invoiceId.trim() || !replyText.trim()}
              onClick={() => void handleInject()}
              aria-label="Process simulated reply"
              className="rounded-2xl bg-gradient-to-r from-indigo-500 via-purple-600 to-pink-600 px-5 py-2.5 text-xs font-bold text-white shadow-lg shadow-indigo-500/25 hover:scale-105 transition-all disabled:opacity-50"
            >
              {busy ? "Processing..." : "Process Reply →"}
            </button>
          </div>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2 pt-1">
        <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400 mr-1">Preset Samples:</span>
        {PRESETS.map((p) => (
          <button
            key={p.label}
            type="button"
            onClick={() => setReplyText(p.text)}
            className="glass-card rounded-xl px-3 py-1.5 text-[11px] font-semibold text-slate-300 hover:border-indigo-400/40 hover:text-white transition-all shadow-sm"
          >
            {p.label}
          </button>
        ))}
      </div>

      {result ? (
        <div className="rounded-xl border border-indigo-500/30 bg-indigo-950/30 p-3 text-xs text-indigo-300 flex items-center gap-2">
          <svg className="h-4 w-4 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span>{result}</span>
        </div>
      ) : null}
    </div>
  );
}

export default ReplySimulator;
