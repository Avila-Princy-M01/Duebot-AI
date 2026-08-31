"use client";

import { useEffect, useState } from "react";
import type { InvoiceRow } from "../../lib/types";
import { listInvoices } from "../../lib/api";
import { formatDateShort, formatINR } from "../../lib/format";
import { EdgeCaseBadge, edgeCaseMeta } from "./EdgeCaseBadge";
import { NudgeModal } from "./NudgeModal";
import { SeedButton } from "../ui/SeedButton";

interface InvoiceTableInteractiveProps {
  initialInvoices: InvoiceRow[];
}

const STATE_LABELS: Record<string, string> = {
  created: "Created",
  overdue: "Overdue",
  nudged: "Nudged",
  replied: "Replied",
  promised: "Promised",
  reminded: "Reminded",
  recovered: "Recovered",
  disputed: "Disputed",
  escalated: "Escalated",
  human_review: "Human Review",
  opted_out: "Opted Out",
  terminated: "Terminated",
};

export function InvoiceTableInteractive({ initialInvoices }: InvoiceTableInteractiveProps) {
  const [invoices, setInvoices] = useState<InvoiceRow[]>(initialInvoices);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [agingFilter, setAgingFilter] = useState<string>("ALL");
  const [riskFilter, setRiskFilter] = useState<string>("ALL");
  const [sortBy, setSortBy] = useState<string>("default");
  const [edgeFilter, setEdgeFilter] = useState<string>("ALL");
  const [activeNudgeId, setActiveNudgeId] = useState<string | null>(null);

  useEffect(() => {
    setInvoices(initialInvoices);
  }, [initialInvoices]);

  const refreshInvoices = () => {
    void listInvoices()
      .then((res) => setInvoices(res.data ?? []))
      .catch(() => {});
  };

  const getAgingBucket = (days: number): string => {
    if (days <= 0) return "current";
    if (days <= 30) return "0-30";
    if (days <= 60) return "31-60";
    if (days <= 90) return "61-90";
    return "90+";
  };

  const RISK_WEIGHTS: Record<string, number> = {
    critical: 4,
    high: 3,
    medium: 2,
    low: 1,
  };

  const filtered = invoices
    .filter((inv) => {
      const needle = search.toLowerCase().trim();
      const matchesSearch =
        needle === "" ||
        inv.invoice_number.toLowerCase().includes(needle) ||
        inv.buyer_id.toLowerCase().includes(needle) ||
        inv.buyer_company_name.toLowerCase().includes(needle) ||
        inv.buyer_contact_name.toLowerCase().includes(needle) ||
        inv.invoice_id.toLowerCase().includes(needle);

      const matchesStatus =
        statusFilter === "ALL" ||
        inv.status.toLowerCase() === statusFilter.toLowerCase() ||
        inv.state.toLowerCase() === statusFilter.toLowerCase();

      const matchesAging =
        agingFilter === "ALL" || getAgingBucket(inv.days_overdue) === agingFilter;

      const matchesRisk =
        riskFilter === "ALL" || inv.risk_tier.toLowerCase() === riskFilter.toLowerCase();

      const matchesEdge = edgeFilter === "ALL" || inv.edge_case === edgeFilter;

      return matchesSearch && matchesStatus && matchesAging && matchesRisk && matchesEdge;
    })
    .sort((a, b) => {
      if (sortBy === "risk_desc") {
        return (RISK_WEIGHTS[b.risk_tier.toLowerCase()] ?? 0) - (RISK_WEIGHTS[a.risk_tier.toLowerCase()] ?? 0);
      }
      if (sortBy === "days_desc") {
        return b.days_overdue - a.days_overdue;
      }
      if (sortBy === "days_asc") {
        return a.days_overdue - b.days_overdue;
      }
      if (sortBy === "amount_desc") {
        return Number(b.outstanding_amount) - Number(a.outstanding_amount);
      }
      return 0;
    });

  const getRiskBadge = (tier: string) => {
    switch (tier.toLowerCase()) {
      case "critical":
        return "bg-rose-500/10 text-rose-400 border-rose-500/30";
      case "high":
        return "bg-amber-500/10 text-amber-400 border-amber-500/30";
      case "medium":
        return "bg-sky-500/10 text-sky-400 border-sky-500/30";
      default:
        return "bg-emerald-500/10 text-emerald-400 border-emerald-500/30";
    }
  };

  const getStateBadge = (state: string) => {
    switch (state.toLowerCase()) {
      case "recovered":
      case "paid":
        return "bg-emerald-500/10 text-emerald-400 border-emerald-500/30";
      case "human_review":
        return "bg-amber-500/10 text-amber-300 border-amber-500/30";
      case "disputed":
      case "escalated":
        return "bg-rose-500/10 text-rose-400 border-rose-500/30";
      case "opted_out":
      case "terminated":
        return "bg-slate-700/40 text-slate-400 border-slate-600/40";
      case "nudged":
        return "bg-sky-500/10 text-sky-400 border-sky-500/30";
      case "promised":
        return "bg-purple-500/10 text-purple-300 border-purple-500/30";
      default:
        return "bg-slate-800 text-slate-300 border-slate-700";
    }
  };

  const getReliabilityColor = (tier: string) => {
    switch (tier.toLowerCase()) {
      case "reliable":
        return "text-emerald-400";
      case "occasional_late":
        return "text-amber-400";
      case "chronic_late":
        return "text-rose-400";
      default:
        return "text-slate-400";
    }
  };

  const hasActiveFilters =
    search.trim() !== "" ||
    statusFilter !== "ALL" ||
    agingFilter !== "ALL" ||
    riskFilter !== "ALL" ||
    edgeFilter !== "ALL" ||
    sortBy !== "default";

  return (
    <div className="space-y-4">
      {/* Controls & Filter Bar */}
      <div className="glass-panel rounded-3xl p-4 sm:p-5 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between border border-white/[0.08]">
        {/* Search */}
        <div className="relative flex-1 max-w-xs">
          <svg className="absolute left-3.5 top-3 h-4 w-4 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            id="invoice-search-input"
            type="text"
            placeholder="Search invoice #, buyer, ID..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            aria-label="Search invoices"
            className="glass-input w-full rounded-2xl pl-10 pr-4 py-2 text-xs text-white placeholder-slate-500 focus:outline-none"
          />
        </div>

        {/* Filter Dropdowns */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Aging Filter */}
          <label htmlFor="aging-filter-select" className="text-xs font-semibold text-slate-400">
            Ageing:
          </label>
          <select
            id="aging-filter-select"
            value={agingFilter}
            onChange={(e) => setAgingFilter(e.target.value)}
            className="rounded-xl border border-slate-700 bg-slate-900 px-3 py-1.5 text-xs text-slate-200 focus:border-sky-500 focus:outline-none"
          >
            <option value="ALL">All Ageing</option>
            <option value="current">Current (0d)</option>
            <option value="0-30">0–30 Days</option>
            <option value="31-60">31–60 Days</option>
            <option value="61-90">61–90 Days</option>
            <option value="90+">90+ Days</option>
          </select>

          {/* Risk Filter */}
          <label htmlFor="risk-filter-select" className="text-xs font-semibold text-slate-400 ml-1">
            Risk:
          </label>
          <select
            id="risk-filter-select"
            value={riskFilter}
            onChange={(e) => setRiskFilter(e.target.value)}
            className="rounded-xl border border-slate-700 bg-slate-900 px-3 py-1.5 text-xs text-slate-200 focus:border-sky-500 focus:outline-none"
          >
            <option value="ALL">All Risk</option>
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
            <option value="critical">Critical</option>
          </select>

          {/* Sort By */}
          <label htmlFor="sort-filter-select" className="text-xs font-semibold text-slate-400 ml-1">
            Sort:
          </label>
          <select
            id="sort-filter-select"
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            className="rounded-xl border border-slate-700 bg-slate-900 px-3 py-1.5 text-xs text-slate-200 focus:border-sky-500 focus:outline-none"
          >
            <option value="default">Default</option>
            <option value="risk_desc">Risk: High → Low</option>
            <option value="days_desc">Days: High → Low</option>
            <option value="days_asc">Days: Low → High</option>
            <option value="amount_desc">Amount: High → Low</option>
          </select>

          {/* State Filter */}
          <label htmlFor="state-filter-select" className="text-xs font-semibold text-slate-400 ml-1">
            State:
          </label>
          <select
            id="state-filter-select"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="rounded-xl border border-slate-700 bg-slate-900 px-3 py-1.5 text-xs text-slate-200 focus:border-sky-500 focus:outline-none"
          >
            <option value="ALL">All States</option>
            {Object.entries(STATE_LABELS).map(([k, v]) => (
              <option key={k} value={k}>
                {v}
              </option>
            ))}
          </select>

          {/* Edge Filter */}
          <label htmlFor="edge-filter-select" className="text-xs font-semibold text-slate-400 ml-1">
            Test Case:
          </label>
          <select
            id="edge-filter-select"
            value={edgeFilter}
            onChange={(e) => setEdgeFilter(e.target.value)}
            className="rounded-xl border border-slate-700 bg-slate-900 px-3 py-1.5 text-xs text-slate-200 focus:border-sky-500 focus:outline-none"
          >
            <option value="ALL">All Cases</option>
            <option value="none">Standard Invoices</option>
            <option value="broken_promise">Broken Promise</option>
            <option value="disputed_balance">Disputed Balance</option>
            <option value="opted_out_buyer">Opted-Out Buyer</option>
            <option value="chronic_late_high_value">Chronic Late / High Value</option>
            <option value="first_time_overdue_reliable">Reliable / First Overdue</option>
            <option value="contact_cap_reached">Contact Cap (Spam Guard)</option>
          </select>

          {hasActiveFilters && (
            <button
              type="button"
              onClick={() => {
                setSearch("");
                setStatusFilter("ALL");
                setAgingFilter("ALL");
                setRiskFilter("ALL");
                setSortBy("default");
                setEdgeFilter("ALL");
              }}
              className="rounded-xl border border-rose-500/30 bg-rose-500/10 px-3 py-1.5 text-xs font-semibold text-rose-300 hover:bg-rose-500/20 transition-all"
            >
              Clear Filters
            </button>
          )}
        </div>
      </div>

      {/* Table Panel */}
      <div className="glass-panel overflow-hidden rounded-3xl border border-white/[0.08]">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="border-b border-white/[0.08] bg-slate-900/90 font-bold uppercase tracking-wider text-slate-300">
              <tr>
                <th className="px-4 py-3.5">Invoice #</th>
                <th className="px-4 py-3.5">Buyer</th>
                <th className="px-4 py-3.5">Amount / Outstanding</th>
                <th className="px-4 py-3.5">Due Date</th>
                <th className="px-4 py-3.5">Ageing</th>
                <th className="px-4 py-3.5">Risk Tier</th>
                <th className="px-4 py-3.5">Lifecycle State</th>
                <th className="px-4 py-3.5 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.06] font-sans">
              {invoices.length === 0 ? (
                /* Empty State 1: Database Unseeded */
                <tr>
                  <td colSpan={8} className="px-4 py-12 text-center">
                    <div className="max-w-md mx-auto space-y-3">
                      <div className="h-12 w-12 rounded-2xl bg-slate-800 border border-slate-700 mx-auto flex items-center justify-center text-slate-400">
                        <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                        </svg>
                      </div>
                      <h4 className="text-sm font-bold text-white">No Invoices Loaded</h4>
                      <p className="text-xs text-slate-400">
                        The receivables ledger is currently empty. Click the button below to seed a realistic portfolio of 260 synthetic B2B invoices.
                      </p>
                      <div className="pt-2 flex justify-center">
                        <SeedButton onSeeded={refreshInvoices} />
                      </div>
                    </div>
                  </td>
                </tr>
              ) : filtered.length === 0 ? (
                /* Empty State 2: Filter resulted in 0 matches */
                <tr>
                  <td colSpan={8} className="px-4 py-10 text-center">
                    <div className="space-y-2">
                      <p className="text-xs text-slate-300 font-semibold">
                        No invoices match the selected filter criteria.
                      </p>
                      <p className="text-xs text-slate-500">
                        Try clearing your search keyword or resetting the state filter.
                      </p>
                      <button
                        type="button"
                        onClick={() => {
                          setSearch("");
                          setStatusFilter("ALL");
                          setEdgeFilter("ALL");
                        }}
                        className="mt-1 inline-flex items-center gap-1 rounded-xl border border-sky-500/30 bg-sky-500/10 px-3 py-1.5 text-xs font-bold text-sky-400 hover:bg-sky-500 hover:text-white transition-all"
                      >
                        Reset Filters (Show {invoices.length} Invoices)
                      </button>
                    </div>
                  </td>
                </tr>
              ) : (
                filtered.map((inv) => {
                  const total = Number(inv.total_amount);
                  const outstanding = Number(inv.outstanding_amount);
                  const isPartial = outstanding > 0 && outstanding < total;
                  const isSettled = outstanding === 0;

                  return (
                    <tr key={inv.invoice_id} className="transition-colors hover:bg-white/[0.03]">
                      <td className="px-4 py-3.5 font-mono font-bold text-sky-400">
                        <a
                          href={`/invoices/${inv.invoice_id}`}
                          className="hover:underline"
                        >
                          {inv.invoice_number}
                        </a>
                        {inv.edge_case && inv.edge_case !== "none" ? (
                          <div className="mt-1">
                            <EdgeCaseBadge edgeCase={inv.edge_case} />
                          </div>
                        ) : null}
                      </td>

                      <td className="px-4 py-3.5">
                        <a href={`/buyers/${inv.buyer_id}`} className="group block">
                          <span className="font-semibold text-white group-hover:underline">
                            {inv.buyer_company_name}
                          </span>
                          <span className="mt-0.5 block text-[11px] text-slate-400">
                            {inv.buyer_contact_name}
                            <span className="mx-1 text-slate-600">|</span>
                            <span
                              className={getReliabilityColor(inv.buyer_reliability_tier)}
                              title={`Historic on-time payment rate: ${(inv.buyer_on_time_payment_rate * 100).toFixed(0)}%`}
                            >
                              {inv.buyer_reliability_tier.replace(/_/g, " ")}{" "}
                              {(inv.buyer_on_time_payment_rate * 100).toFixed(0)}%
                            </span>
                          </span>
                        </a>
                      </td>

                      <td className="px-4 py-3.5">
                        <span className="block font-mono font-bold text-white">
                          {formatINR(inv.total_amount)}
                        </span>
                        {isSettled ? (
                          <span className="mt-0.5 block text-xs font-bold uppercase text-emerald-400">
                            Settled
                          </span>
                        ) : isPartial ? (
                          <span
                            className="mt-0.5 block font-mono text-xs font-bold text-amber-300"
                            title={`${formatINR(inv.amount_paid)} already paid`}
                          >
                            {formatINR(outstanding)} outstanding
                          </span>
                        ) : (
                          <span className="mt-0.5 block font-mono text-xs text-slate-400">
                            {formatINR(outstanding)}
                          </span>
                        )}
                      </td>

                      <td className="px-4 py-3.5 text-slate-300">
                        {formatDateShort(inv.due_date)}
                      </td>

                      <td className="px-4 py-3.5">
                        {inv.days_overdue > 0 ? (
                          <span className="font-bold text-rose-400">
                            {inv.days_overdue}d overdue
                          </span>
                        ) : isSettled ? (
                          <span className="text-emerald-400 font-semibold">Settled</span>
                        ) : (
                          <span className="text-slate-400">Current</span>
                        )}
                      </td>

                      <td className="px-4 py-3.5">
                        <span
                          className={`inline-flex rounded-full border px-2.5 py-0.5 text-xs font-extrabold uppercase ${getRiskBadge(inv.risk_tier)}`}
                        >
                          {inv.risk_tier}
                        </span>
                      </td>

                      <td className="px-4 py-3.5">
                        <span
                          className={`inline-flex rounded-full border px-2.5 py-0.5 text-xs font-extrabold uppercase ${getStateBadge(inv.state)}`}
                        >
                          {STATE_LABELS[inv.state] ?? inv.state}
                        </span>
                      </td>

                      <td className="px-4 py-3.5 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <button
                            type="button"
                            onClick={() => setActiveNudgeId(inv.invoice_id)}
                            className="rounded-xl border border-sky-500/30 bg-sky-500/10 px-3 py-1.5 text-xs font-bold text-sky-300 hover:bg-sky-500 hover:text-white transition-all shadow-sm"
                          >
                            Nudge →
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {activeNudgeId ? (
        <NudgeModal
          invoiceId={activeNudgeId}
          onClose={() => {
            setActiveNudgeId(null);
            refreshInvoices();
          }}
        />
      ) : null}
    </div>
  );
}

export default InvoiceTableInteractive;
