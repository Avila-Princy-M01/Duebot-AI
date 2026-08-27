"use client";

import { useEffect, useRef, useState } from "react";
import { ReplySimulator } from "./ReplySimulator";
import { SeedButton } from "../ui/SeedButton";
import { listInbox } from "../../lib/api";
import type { InboxRow } from "../../lib/types";

interface InboxInteractiveProps {
  initialRows: InboxRow[];
}

export function InboxInteractive({ initialRows }: InboxInteractiveProps) {
  const [rows, setRows] = useState<InboxRow[]>(initialRows);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<string>("ALL");
  const [liveSync, setLiveSync] = useState<boolean>(false);
  const [highlightedId, setHighlightedId] = useState<string | null>(null);
  const listTopRef = useRef<HTMLDivElement>(null);

  const loadInbox = (targetInvoiceId?: string) => {
    setLoading(true);
    listInbox()
      .then((res) => {
        const data = res.data ?? [];
        setRows(data);
        setError(null);

        if (targetInvoiceId && data.length > 0) {
          // Find the most recent inbound message for this invoice
          const matching = data.find(
            (r) => r.invoice_id === targetInvoiceId && r.direction === "inbound"
          );
          if (matching) {
            setHighlightedId(matching.interaction_id);
            setTimeout(() => {
              const el = document.getElementById(`msg-${matching.interaction_id}`);
              if (el) {
                el.scrollIntoView({ behavior: "smooth", block: "center" });
              }
            }, 100);
            // Clear highlight after 8 seconds
            setTimeout(() => setHighlightedId(null), 8000);
          }
        }
      })
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "Failed to load inbox"))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    if (!liveSync) return;
    const interval = setInterval(() => {
      listInbox()
        .then((res) => setRows(res.data ?? []))
        .catch(() => {});
    }, 5000);
    return () => clearInterval(interval);
  }, [liveSync]);

  const filtered = rows.filter((r) => {
    if (filter === "OUTBOUND") return r.direction === "outbound";
    if (filter === "INBOUND") return r.direction === "inbound";
    return true;
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-2xl font-extrabold tracking-tight text-white">WhatsApp Communication Inbox</h1>
          <p className="text-xs text-slate-300">
            Real-time audit log of outbound Razorpay WhatsApp nudges and inbound buyer replies.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <label className="flex items-center gap-2 rounded-xl border border-slate-800 bg-panel px-3 py-1.5 text-xs text-slate-300 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={liveSync}
              onChange={(e) => setLiveSync(e.target.checked)}
              className="rounded bg-slate-800 border-slate-700 text-sky-500 focus:ring-0"
            />
            <span className="font-semibold">Live Poll (5s)</span>
          </label>

          <button
            type="button"
            onClick={() => loadInbox()}
            disabled={loading}
            className="flex items-center gap-2 rounded-xl border border-slate-700 bg-slate-800/80 px-3.5 py-1.5 text-xs font-semibold text-slate-200 hover:bg-slate-700 hover:text-white transition-all shadow-sm disabled:opacity-60"
          >
            <span className={`h-2 w-2 rounded-full ${loading ? "bg-amber-400 animate-pulse" : "bg-emerald-400"}`} />
            <span>{loading ? "Refreshing..." : "Refresh Feed"}</span>
          </button>

          <span className="rounded-xl border border-sky-500/20 bg-sky-500/10 px-3.5 py-1.5 text-xs font-bold text-sky-400">
            {rows.length} Total Messages
          </span>
        </div>
      </div>

      {/* Interactive Reply Simulator Test Bench */}
      <ReplySimulator onReplyInjected={(invId) => loadInbox(invId)} />

      {/* Messages Filter & List */}
      <div ref={listTopRef} className="space-y-4 pt-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-bold text-white">Interaction Log</h3>
            <span className="text-xs text-slate-400">({filtered.length} visible)</span>
          </div>
          <div className="flex items-center gap-2">
            {["ALL", "OUTBOUND", "INBOUND"].map((f) => (
              <button
                key={f}
                type="button"
                onClick={() => setFilter(f)}
                className={`rounded-lg px-3 py-1 text-xs font-bold transition-all ${
                  filter === f
                    ? "bg-sky-500 text-white shadow-sm shadow-sky-500/20"
                    : "bg-panel border border-slate-800 text-slate-400 hover:bg-slate-800 hover:text-white"
                }`}
              >
                {f}
              </button>
            ))}
          </div>
        </div>

        {error ? (
          <div className="rounded-xl border border-rose-500/30 bg-rose-950/30 p-4 text-xs text-rose-300">
            {error}
          </div>
        ) : null}

        <div className="space-y-3">
          {rows.length === 0 ? (
            /* Empty State 1: No Data in DB */
            <div className="rounded-3xl border border-slate-800/80 bg-panel/60 p-10 text-center space-y-3">
              <div className="flex justify-center">
                <div className="h-12 w-12 rounded-2xl bg-slate-800/80 border border-slate-700 flex items-center justify-center text-slate-400">
                  <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                  </svg>
                </div>
              </div>
              <h4 className="text-sm font-bold text-white">No WhatsApp Messages Logged Yet</h4>
              <p className="text-xs text-slate-400 max-w-md mx-auto">
                The communications inbox is empty. Seed synthetic invoices or simulate a buyer reply using the test bench above.
              </p>
              <div className="pt-2 flex justify-center">
                <SeedButton />
              </div>
            </div>
          ) : filtered.length === 0 ? (
            /* Empty State 2: Filter resulted in 0 matches */
            <div className="rounded-2xl border border-slate-800/80 bg-panel/60 p-8 text-center space-y-2">
              <p className="text-xs text-slate-400">No messages match the current <span className="font-bold text-sky-400">{filter}</span> filter.</p>
              <button
                type="button"
                onClick={() => setFilter("ALL")}
                className="text-xs font-bold text-sky-400 hover:underline"
              >
                Reset filter to show all {rows.length} messages
              </button>
            </div>
          ) : (
            filtered.map((row) => {
              const isOutbound = row.direction === "outbound";
              const isHighlighted = highlightedId === row.interaction_id;

              return (
                <div
                  id={`msg-${row.interaction_id}`}
                  key={row.interaction_id}
                  className={`group relative overflow-hidden rounded-2xl border p-5 backdrop-blur-md transition-all shadow-md ${
                    isHighlighted
                      ? "border-emerald-400 bg-emerald-950/30 ring-2 ring-emerald-400/50 shadow-emerald-500/10 scale-[1.01]"
                      : isOutbound
                        ? "border-slate-800/80 bg-panel/70 hover:border-slate-700"
                        : "border-indigo-500/30 bg-indigo-950/20 hover:border-indigo-500/50"
                  }`}
                >
                  <div className="flex items-center justify-between text-xs mb-2.5">
                    <div className="flex flex-wrap items-center gap-2.5">
                      <span
                        className={`inline-flex rounded-full border px-2.5 py-0.5 text-xs font-extrabold uppercase ${
                          isOutbound
                            ? "bg-sky-500/10 text-sky-400 border-sky-500/30"
                            : "bg-purple-500/10 text-purple-400 border-purple-500/30"
                        }`}
                      >
                        {row.direction}
                      </span>

                      {isHighlighted && (
                        <span className="rounded-full bg-emerald-500/20 border border-emerald-400/40 px-2 py-0.5 text-[10px] font-extrabold text-emerald-300 animate-pulse">
                          ★ Just Injected
                        </span>
                      )}

                      <span className="font-mono text-xs text-slate-300 font-semibold">
                        Invoice: <a href={`/invoices/${row.invoice_id}`} className="text-sky-400 hover:underline">{row.invoice_id}</a>
                      </span>
                      <span className="text-slate-500">•</span>
                      <span className="font-mono text-xs text-slate-400">{row.to_phone_masked}</span>
                    </div>

                    <span className="text-xs text-slate-400 font-mono">WhatsApp Channel</span>
                  </div>

                  <div className="rounded-xl border border-slate-800/60 bg-slate-900/80 p-3.5 font-mono text-xs text-slate-200 leading-relaxed shadow-inner">
                    {row.body}
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}
