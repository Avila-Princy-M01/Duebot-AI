"use client";

import { useEffect, useState } from "react";
import { ReplySimulator } from "../../components/inbox/ReplySimulator";
import { listInbox } from "../../lib/api";
import type { InboxRow } from "../../lib/types";

export default function InboxPage() {
  const [rows, setRows] = useState<InboxRow[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<string>("ALL");

  const loadInbox = () => {
    void listInbox()
      .then((res) => setRows(res.data))
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "Failed to load inbox"));
  };

  useEffect(() => {
    loadInbox();
  }, []);

  const filtered = rows.filter((r) => {
    if (filter === "OUTBOUND") return r.direction === "outbound";
    if (filter === "INBOUND") return r.direction === "inbound";
    return true;
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-2xl font-extrabold tracking-tight text-white">WhatsApp Communication Inbox</h1>
          <p className="text-xs text-slate-400">
            Real-time audit log of outbound Razorpay WhatsApp nudges and inbound buyer replies.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="rounded-xl border border-slate-800 bg-panel px-3 py-1.5 text-xs font-bold text-sky-400">
            {rows.length} Total Messages Logged
          </span>
        </div>
      </div>

      {/* Interactive Reply Simulator */}
      <ReplySimulator onReplyInjected={loadInbox} />

      {/* Messages Filter & List */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-bold text-white">Interaction Log</h3>
          <div className="flex items-center gap-2">
            {["ALL", "OUTBOUND", "INBOUND"].map((f) => (
              <button
                key={f}
                type="button"
                onClick={() => setFilter(f)}
                className={`rounded-lg px-2.5 py-1 text-[11px] font-bold transition-all ${
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
          {filtered.length === 0 ? (
            <div className="rounded-2xl border border-slate-800/80 bg-panel/60 p-8 text-center text-xs text-slate-500">
              No interactions logged yet. Click "Seed synthetic batch" or simulate a buyer reply above.
            </div>
          ) : (
            filtered.map((row) => {
              const isOutbound = row.direction === "outbound";
              return (
                <div
                  key={row.interaction_id}
                  className={`group relative overflow-hidden rounded-2xl border ${
                    isOutbound ? "border-slate-800/80 bg-panel/70" : "border-indigo-500/30 bg-indigo-950/20"
                  } p-5 backdrop-blur-md transition-all hover:border-slate-700 shadow-md`}
                >
                  <div className="flex items-center justify-between text-xs mb-2">
                    <div className="flex items-center gap-2">
                      <span
                        className={`inline-flex rounded-full border px-2.5 py-0.5 text-[10px] font-extrabold uppercase ${
                          isOutbound
                            ? "bg-sky-500/10 text-sky-400 border-sky-500/30"
                            : "bg-purple-500/10 text-purple-400 border-purple-500/30"
                        }`}
                      >
                        {row.direction}
                      </span>
                      <span className="font-mono text-slate-400">Invoice: {row.invoice_id}</span>
                      <span className="text-slate-500">•</span>
                      <span className="font-mono text-slate-400">{row.to_phone_masked}</span>
                    </div>

                    <span className="text-[11px] text-slate-500 font-mono">WhatsApp Channel</span>
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
