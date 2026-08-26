"use client";

import { useCallback, useEffect, useState } from "react";
import { AuditLog } from "../../components/audit/AuditLog";
import { listAudit, verifyAudit } from "../../lib/api";
import type { AuditRow, AuditVerification } from "../../lib/types";

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
  const [verification, setVerification] = useState<AuditVerification | null>(null);
  const [showProofModal, setShowProofModal] = useState<boolean>(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Filters & Pagination
  const [selectedState, setSelectedState] = useState<string>("");
  const [selectedActor, setSelectedActor] = useState<string>("");
  const [invoiceSearch, setInvoiceSearch] = useState<string>("");
  const [limit, setLimit] = useState<number>(50);
  const [offset, setOffset] = useState<number>(0);

  const loadAudit = useCallback(() => {
    setLoading(true);
    Promise.all([
      listAudit({
        to_state: selectedState || undefined,
        actor: selectedActor || undefined,
        invoice_id: invoiceSearch.trim() || undefined,
        limit,
        offset,
      }),
      verifyAudit(),
    ])
      .then(([auditRes, verifyRes]) => {
        setRows(auditRes.data);
        setTotalCount(auditRes.meta.total_count);
        setVerification(verifyRes.data);
        setError(null);
      })
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : "Failed to load audit logs");
      })
      .finally(() => setLoading(false));
  }, [selectedState, selectedActor, invoiceSearch, limit, offset]);

  useEffect(() => {
    loadAudit();
    const interval = setInterval(loadAudit, 15000);
    return () => clearInterval(interval);
  }, [loadAudit]);

  const total = totalCount ?? rows.length;
  const currentPage = Math.floor(offset / limit) + 1;
  const totalPages = Math.max(1, Math.ceil(total / limit));
  const fromRecord = total === 0 ? 0 : offset + 1;
  const toRecord = Math.min(offset + limit, total);

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
            Immutable, cryptographically verifiable SHA-256 ledger of every state transition, LLM confidence judgment, and operator decision.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {/* Cryptographic Chain Verification Badge */}
          {verification ? (
            <button
              type="button"
              onClick={() => setShowProofModal(!showProofModal)}
              className={`flex items-center gap-1.5 rounded-xl border px-3.5 py-2 text-xs font-bold transition-all shadow-sm ${
                verification.valid
                  ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300 hover:bg-emerald-500/20"
                  : "border-rose-500/30 bg-rose-500/10 text-rose-300 hover:bg-rose-500/20"
              }`}
            >
              <span className={`h-2 w-2 rounded-full ${verification.valid ? "bg-emerald-400" : "bg-rose-400"}`} />
              <span>
                {verification.valid
                  ? `Chain Verified ✓ (${verification.rows_verified} blocks)`
                  : "Tamper Detected ⚠️"}
              </span>
            </button>
          ) : null}

          <button
            type="button"
            onClick={loadAudit}
            className="flex items-center gap-1.5 rounded-xl border border-slate-800 bg-panel px-3.5 py-2 text-xs font-semibold text-slate-300 hover:bg-slate-800 hover:text-white transition-all shadow-sm"
          >
            <span className={`h-2 w-2 rounded-full ${loading ? "bg-amber-400 animate-ping" : "bg-emerald-400"}`} />
            <span>{loading ? "Refreshing..." : "Refresh Feed"}</span>
          </button>
          <span className="rounded-xl border border-sky-500/20 bg-sky-500/10 px-3.5 py-2 text-xs font-extrabold text-sky-400">
            {total} Total Transitions Logged
          </span>
        </div>
      </div>

      {/* Cryptographic Proof Card (Expandable) */}
      {showProofModal && verification ? (
        <div className="glass-panel p-5 rounded-2xl border border-emerald-500/30 bg-emerald-950/20 space-y-3 animate-in fade-in slide-in-from-top-2 duration-200">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-emerald-400 text-sm">🔒</span>
              <h3 className="text-sm font-bold text-emerald-300">
                Cryptographic Audit Trail Proof (SHA-256 Merkle Chain)
              </h3>
            </div>
            <button
              type="button"
              onClick={() => setShowProofModal(false)}
              className="text-xs text-slate-400 hover:text-white font-mono"
            >
              ✕ Close
            </button>
          </div>
          <p className="text-xs text-slate-300">
            Every audit log entry contains a cryptographic signature linking directly to its parent transition block (<code className="font-mono text-emerald-400">row_hash = SHA256(canonical_json(row) + prev_hash)</code>). Any retroactive row mutation or insertion immediately breaks subsequent chain hashes.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-2 text-xs">
            <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-3">
              <div className="text-[10px] uppercase font-bold text-slate-400">Chain Integrity Status</div>
              <div className="text-sm font-extrabold text-emerald-400 mt-0.5">
                {verification.valid ? "100% Tamper-Evident Valid" : "Tamper Detected"}
              </div>
              <div className="text-[10px] text-slate-500 mt-1">Verified: {verification.rows_verified} of {total} blocks</div>
            </div>
            <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-3 md:col-span-2">
              <div className="text-[10px] uppercase font-bold text-slate-400">Latest Block Hash (Tip of Chain)</div>
              <div className="font-mono text-xs text-sky-300 break-all mt-0.5">
                {verification.latest_hash}
              </div>
              <div className="text-[10px] text-slate-500 mt-1 font-mono">
                Genesis Root: {verification.genesis_hash.slice(0, 16)}… (All 64 zeros)
              </div>
            </div>
          </div>
        </div>
      ) : null}

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
            onChange={(e) => {
              setSelectedState(e.target.value);
              setOffset(0);
            }}
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
            onChange={(e) => {
              setSelectedActor(e.target.value);
              setOffset(0);
            }}
            className="glass-input rounded-xl px-3 py-1.5 text-xs text-slate-200 bg-slate-900/90 border border-slate-700/60 focus:border-sky-500 focus:outline-none"
          >
            {ACTOR_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        {/* Search by Invoice ID (Partial ilike search) */}
        <div className="flex items-center gap-1.5 flex-1 min-w-[200px]">
          <label htmlFor="invoice-search" className="text-xs font-semibold text-slate-400">
            Search:
          </label>
          <input
            id="invoice-search"
            type="text"
            placeholder="Invoice ID (e.g. INV-15, 15c3)"
            value={invoiceSearch}
            onChange={(e) => {
              setInvoiceSearch(e.target.value);
              setOffset(0);
            }}
            className="glass-input w-full rounded-xl px-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 bg-slate-900/90 border border-slate-700/60 focus:border-sky-500 focus:outline-none"
          />
        </div>

        {/* Row Limit */}
        <div className="flex items-center gap-1.5">
          <label htmlFor="limit-select" className="text-xs font-semibold text-slate-400">
            Page Size:
          </label>
          <select
            id="limit-select"
            value={limit}
            onChange={(e) => {
              setLimit(Number(e.target.value));
              setOffset(0);
            }}
            className="glass-input rounded-xl px-3 py-1.5 text-xs text-slate-200 bg-slate-900/90 border border-slate-700/60 focus:border-sky-500 focus:outline-none"
          >
            <option value={25}>25</option>
            <option value={50}>50</option>
            <option value={100}>100</option>
            <option value={200}>200</option>
            <option value={500}>500 (All)</option>
          </select>
        </div>

        {/* Reset Button */}
        {selectedState || selectedActor || invoiceSearch ? (
          <button
            type="button"
            onClick={() => {
              setSelectedState("");
              setSelectedActor("");
              setInvoiceSearch("");
              setOffset(0);
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

      {/* Main Audit Feed */}
      <AuditLog rows={rows} />

      {/* Pagination Controls */}
      <div className="glass-panel p-4 rounded-2xl flex flex-col sm:flex-row items-center justify-between gap-4 border border-white/[0.08]">
        <div className="text-xs text-slate-400">
          Showing <span className="font-semibold text-slate-200">{fromRecord}</span> to{" "}
          <span className="font-semibold text-slate-200">{toRecord}</span> of{" "}
          <span className="font-bold text-sky-400">{total}</span> transitions
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            disabled={offset === 0 || loading}
            onClick={() => setOffset(Math.max(0, offset - limit))}
            className="rounded-xl border border-slate-800 bg-panel px-3 py-1.5 text-xs font-semibold text-slate-300 hover:bg-slate-800 hover:text-white disabled:opacity-40 disabled:cursor-not-allowed transition-all"
          >
            ← Previous
          </button>

          <span className="px-3 py-1 text-xs font-semibold text-slate-300 bg-slate-900/90 rounded-lg border border-slate-800">
            Page {currentPage} of {totalPages}
          </span>

          <button
            type="button"
            disabled={offset + limit >= total || loading}
            onClick={() => setOffset(offset + limit)}
            className="rounded-xl border border-slate-800 bg-panel px-3 py-1.5 text-xs font-semibold text-slate-300 hover:bg-slate-800 hover:text-white disabled:opacity-40 disabled:cursor-not-allowed transition-all"
          >
            Next →
          </button>
        </div>
      </div>
    </div>
  );
}
