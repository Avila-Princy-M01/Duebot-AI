"use client";

import { useEffect, useState } from "react";
import { ReplySimulator } from "../../components/inbox/ReplySimulator";
import { listInbox } from "../../lib/api";
import type { InboxRow } from "../../lib/types";

export default function InboxPage() {
  const [rows, setRows] = useState<InboxRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<string>("ALL");
  const [liveSync, setLiveSync] = useState<boolean>(false);

  const loadInbox = () => {
    setLoading(true);
    listInbox()
      .then((res) => {
        setRows(res.data ?? []);
        setError(null);
      })
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "Failed to load inbox"))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadInbox();
  }, []);

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
            Audit log of outbound Razorpay WhatsApp nudges and inbound buyer replies.
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
            onClick={loadInbox}
            disabled={loading}
            className="flex items-center gap-2 rounded-xl border border-slate-700 bg-slate-800/80 px-3.5 py-1.5 text-xs font-semibold text-slate-200 hover:bg-slate-700 hover:text-white transition-all shadow-sm disabled:opacity-60"
          >
            <span className={`h-2 w-2 rounded-full ${loading ? "bg-amber-400 animate-pulse" : "bg-emerald-400"}`} />
            <span>{loading ? "Refreshing..." : "Refresh"}</span>
          </button>

          <span className="rounded-xl border border-slate-800 bg-panel px-3 py-1.5 text-xs font-bold text-sky-400">
            {rows.length} Messages
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
          {filtered.length === 0 ? (
            <div className="rounded-2xl border border-slate-800/80 bg-panel/60 p-8 text-center text-xs text-slate-400">
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
                    <div className="flex items-center gap-2.5">
                      <span
                        className={`inline-flex rounded-full border px-2.5 py-0.5 text-xs font-extrabold uppercase ${
                          isOutbound
                            ? "bg-sky-500/10 text-sky-400 border-sky-500/30"
                            : "bg-purple-500/10 text-purple-400 border-purple-500/30"
                        }`}
                      >
                        {row.direction}
                      </span>
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
