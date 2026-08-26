"use client";

import { useCallback, useEffect, useState } from "react";
import { AuditLog } from "../../components/audit/AuditLog";
import { listAudit } from "../../lib/api";
import type { AuditRow } from "../../lib/types";

const STATE_OPTIONS = [
  { value: "", label: "All States" },
  { value: "human_review", label: "Human Review" },
  { value: "disputed", label: "Disputed" },
  { value: "opted_out", label: "Opted Out" },
  { value: "recovered", label: "Recovered" },
  { value: "promised", label: "Promised" },
  { value: "reminded", label: "Reminded" },
  { value: "escalated", label: "Escalated" },
  { value: "nudged", label: "Nudged" },
  { value: "overdue", label: "Overdue" },
  { value: "terminated", label: "Terminated" },
];

const ACTOR_OPTIONS = [
  { value: "", label: "All Actors" },
  { value: "agent", label: "Agent (Deterministic)" },
  { value: "human", label: "Human (Merchant/Reviewer)" },
  { value: "system", label: "System (Webhook/Clock)" },
];

export default function AuditPage() {
  const [rows, setRows] = useState<AuditRow[]>([]);
  const [totalCount, setTotalCount] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [selectedState, setSelectedState] = useState<string>("");
  const [selectedActor, setSelectedActor] = useState<string>("");
  const [invoiceSearch, setInvoiceSearch] = useState<string>("");
  const [limit, setLimit] = useState<number>(100);

  const loadAudit = useCallback(() => {
    setLoading(true);
    listAudit({
      to_state: selectedState || undefined,
      actor: selectedActor || undefined,
      invoice_id: invoiceSearch.trim() || undefined,
      limit,
    })
      .then((res) => {
        setRows(res.data);
        setTotalCount(res.meta.total_count);
        setError(null);
      })
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : "Failed to load audit logs");
      })
      .finally(() => setLoading(false));
  }, [selectedState, selectedActor, invoiceSearch, limit]);

  useEffect(() => {
    loadAudit();
    const interval = setInterval(loadAudit, 15000);
    return () => clearInterval(interval);
  }, [loadAudit]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-extrabold tracking-tight text-white">Append-Only Policy Audit Log</h1>
            <span className="rounded-full bg-emerald-500/10 border border-emerald-500/30 px-2 py-0.5 text-[10px] font-bold text-emerald-400">
              Policy v1.0.0
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Immutable, cryptographically verifiable ledger of every state transition, LLM confidence judgment, and human operator action.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={loadAudit}
            className="flex items-center gap-1.5 rounded-xl border border-slate-800 bg-panel px-3.5 py-2 text-xs font-semibold text-slate-300 hover:bg-slate-800 hover:text-white transition-all shadow-sm"
          >
            <span className={`h-2 w-2 rounded-full ${loading ? "bg-amber-400 animate-ping" : "bg-emerald-400"}`} />
            <span>{loading ? "Refreshing..." : "Refresh Feed"}</span>
          </button>
          <span className="rounded-xl border border-sky-500/20 bg-sky-500/10 px-3.5 py-2 text-xs font-extrabold text-sky-400">
            {totalCount !== null ? totalCount : rows.length} Total Transitions Logged
          </span>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="glass-panel p-4 rounded-2xl flex flex-wrap items-center gap-3 border border-white/[0.08]">
        {/* State Filter */}
        <div className="flex items-center gap-1.5">
          <label htmlFor="state-filter" className="text-xs font-semibold text-slate-400">
            Target State:
          </label>
          <select
            id="state-filter"
            value={selectedState}
            onChange={(e) => setSelectedState(e.target.value)}
            className="glass-input rounded-xl px-3 py-1.5 text-xs text-slate-200 bg-slate-900/90 border border-slate-700/60 focus:border-sky-500 focus:outline-none"
          >
            {STATE_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        {/* Actor Filter */}
        <div className="flex items-center gap-1.5">
          <label htmlFor="actor-filter" className="text-xs font-semibold text-slate-400">
            Actor:
          </label>
          <select
            id="actor-filter"
            value={selectedActor}
            onChange={(e) => setSelectedActor(e.target.value)}
            className="glass-input rounded-xl px-3 py-1.5 text-xs text-slate-200 bg-slate-900/90 border border-slate-700/60 focus:border-sky-500 focus:outline-none"
          >
            {ACTOR_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        {/* Search by Invoice ID */}
        <div className="flex items-center gap-1.5 flex-1 min-w-[200px]">
          <label htmlFor="invoice-search" className="text-xs font-semibold text-slate-400">
            Search:
          </label>
          <input
            id="invoice-search"
            type="text"
            placeholder="Invoice ID (e.g. INV-1234)"
            value={invoiceSearch}
            onChange={(e) => setInvoiceSearch(e.target.value)}
            className="glass-input w-full rounded-xl px-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 bg-slate-900/90 border border-slate-700/60 focus:border-sky-500 focus:outline-none"
          />
        </div>

        {/* Row Limit */}
        <div className="flex items-center gap-1.5">
          <label htmlFor="limit-select" className="text-xs font-semibold text-slate-400">
            Limit:
          </label>
          <select
            id="limit-select"
            value={limit}
            onChange={(e) => setLimit(Number(e.target.value))}
            className="glass-input rounded-xl px-3 py-1.5 text-xs text-slate-200 bg-slate-900/90 border border-slate-700/60 focus:border-sky-500 focus:outline-none"
          >
            <option value={50}>50</option>
            <option value={100}>100</option>
            <option value={200}>200</option>
          </select>
        </div>

        {/* Reset Button */}
        {(selectedState || selectedActor || invoiceSearch) ? (
          <button
            type="button"
            onClick={() => {
              setSelectedState("");
              setSelectedActor("");
              setInvoiceSearch("");
            }}
            className="rounded-xl border border-slate-700/80 px-2.5 py-1.5 text-xs text-slate-400 hover:text-white hover:border-slate-500 transition-colors"
          >
            Clear Filters
          </button>
        ) : null}
      </div>

      {error ? (
        <div className="rounded-xl border border-rose-500/30 bg-rose-950/30 p-4 text-xs text-rose-300">
          {error}
        </div>
      ) : null}

      <AuditLog rows={rows} />
    </div>
  );
}
