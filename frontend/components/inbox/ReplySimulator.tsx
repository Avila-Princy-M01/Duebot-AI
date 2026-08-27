"use client";

import { useEffect, useState } from "react";
import { injectReply, listInvoices } from "../../lib/api";

interface ReplySimulatorProps {
  onReplyInjected?: (invoiceId: string) => void;
}

const PRESETS = [
  { text: "Paisa transfer ho jayega Friday tak", label: "Promise (Hinglish)" },
  { text: "Bill total is wrong, rate was 450", label: "Dispute Rate" },
  { text: "Stop sending messages to my WhatsApp number", label: "Opt-Out" },
  { text: "Require physical invoice copy for audit first", label: "Objection" },
  { text: "It's in process, will update shortly", label: "Ambiguous (Abstains to Human Review)" },
];

export function ReplySimulator({ onReplyInjected }: ReplySimulatorProps) {
  const [invoiceId, setInvoiceId] = useState("");
  const [replyText, setReplyText] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<string | null>(null);

  useEffect(() => {
    void listInvoices({ state: "nudged" })
      .then((res) => {
        const first = res.data?.[0] ?? null;
        if (first?.invoice_id) {
          setInvoiceId(first.invoice_id);
        } else {
          void listInvoices().then((allRes) => {
            if (allRes.data?.[0]?.invoice_id) {
              setInvoiceId(allRes.data[0].invoice_id);
            }
          });
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
        setResult(`✓ Reply processed! State transitioned to: ${res.data.state.toUpperCase()}`);
      }
      const sentId = invoiceId.trim();
      setReplyText("");
      if (onReplyInjected) onReplyInjected(sentId);
    } catch (err: unknown) {
      setResult(err instanceof Error ? err.message : "Failed to process reply");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="glass-panel rounded-3xl p-6 sm:p-8 space-y-5 border border-indigo-500/20 shadow-xl relative overflow-hidden">
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-indigo-500/15 text-indigo-400 border border-indigo-400/30 shadow-md shadow-indigo-500/10">
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
          </svg>
        </div>
        <div>
          <h3 className="text-base font-extrabold text-white">Live WhatsApp Reply Test Bench</h3>
          <p className="text-xs text-slate-300">
            Simulate incoming buyer replies to evaluate intent classification, confidence threshold gating, and state transitions in real time.
          </p>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <div>
          <label htmlFor="target-invoice-id-input" className="block text-xs font-bold uppercase tracking-wider text-slate-300 mb-1.5">
            Target Invoice ID
          </label>
          <input
            id="target-invoice-id-input"
            type="text"
            placeholder="e.g. INV-15c3c85ca6"
            value={invoiceId}
            onChange={(e) => setInvoiceId(e.target.value)}
            aria-label="Target Invoice ID"
            className="glass-input w-full rounded-2xl px-3.5 py-2.5 text-xs font-mono text-white focus:outline-none"
          />
        </div>

        <div className="md:col-span-2">
          <label htmlFor="incoming-reply-text-input" className="block text-xs font-bold uppercase tracking-wider text-slate-300 mb-1.5">
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
              className="rounded-2xl bg-gradient-to-r from-indigo-500 via-purple-600 to-pink-600 px-5 py-2.5 text-xs font-bold text-white shadow-lg shadow-indigo-500/25 hover:brightness-110 transition-all disabled:opacity-50 flex items-center gap-1.5"
            >
              <span>{busy ? "Processing..." : "Process Reply →"}</span>
            </button>
          </div>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2 pt-1">
        <span className="text-xs font-bold uppercase tracking-wider text-slate-400 mr-1">Preset Samples:</span>
        {PRESETS.map((p) => (
          <button
            key={p.label}
            type="button"
            onClick={() => setReplyText(p.text)}
            className="glass-card rounded-xl px-3 py-1.5 text-xs font-semibold text-slate-300 hover:border-indigo-400/40 hover:text-white transition-all shadow-sm"
          >
            {p.label}
          </button>
        ))}
      </div>

      {result ? (
        <div className="rounded-2xl border border-indigo-500/30 bg-indigo-950/40 p-4 text-xs font-semibold text-indigo-200 animate-in fade-in slide-in-from-top-1">
          {result}
        </div>
      ) : null}

      {/* Downward visual flow cue connecting simulator to interaction log */}
      <div className="flex items-center justify-center gap-2 pt-2 text-xs font-medium text-slate-400 border-t border-white/[0.06]">
        <svg className="h-4 w-4 text-indigo-400 animate-bounce" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
        </svg>
        <span>Processed replies appear instantly in the Interaction Log below</span>
      </div>
    </div>
  );
}

export default ReplySimulator;
