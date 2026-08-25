"use client";

import { useEffect, useState } from "react";
import type { InvoiceRow } from "../../lib/types";
import { listInvoices } from "../../lib/api";
import { formatDateShort, formatINR } from "../../lib/format";
import { EdgeCaseBadge, edgeCaseMeta } from "./EdgeCaseBadge";
import { NudgeModal } from "./NudgeModal";

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
  const [edgeFilter, setEdgeFilter] = useState<string>("ALL");
  const [activeNudgeId, setActiveNudgeId] = useState<string | null>(null);

  useEffect(() => {
    setInvoices(initialInvoices);
  }, [initialInvoices]);

  const refreshInvoices = () => {
    void listInvoices()
      .then((res) => setInvoices(res.data))
      .catch(() => {});
  };

  const filtered = invoices.filter((inv) => {
    const needle = search.toLowerCase();
    const matchesSearch =
      search === "" ||
      inv.invoice_number.toLowerCase().includes(needle) ||
      inv.buyer_id.toLowerCase().includes(needle) ||
      inv.buyer_company_name.toLowerCase().includes(needle) ||
      inv.buyer_contact_name.toLowerCase().includes(needle) ||
      inv.invoice_id.toLowerCase().includes(needle);

    const matchesStatus =
      statusFilter === "ALL" ||
      inv.status.toLowerCase() === statusFilter.toLowerCase() ||
      inv.state.toLowerCase() === statusFilter.toLowerCase();

    const matchesEdge = edgeFilter === "ALL" || inv.edge_case === edgeFilter;

    return matchesSearch && matchesStatus && matchesEdge;
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
      case "overdue":
        return "bg-rose-500/10 text-rose-400 border-rose-500/20";
      case "recovered":
      case "promised":
        return "bg-emerald-500/10 text-emerald-400 border-emerald-500/20";
      case "human_review":
        return "bg-amber-500/10 text-amber-400 border-amber-500/20 animate-pulse";
      case "escalated":
        return "bg-purple-500/10 text-purple-400 border-purple-500/20";
      default:
        return "bg-slate-800 text-slate-400 border-slate-700";
    }
  };

  const getReliabilityColor = (tier: string) => {
    switch (tier) {
      case "chronic_late":
        return "text-rose-400";
      case "occasional_late":
        return "text-amber-400";
      default:
        return "text-emerald-400";
    }
  };

  // Counts derive from `invoices`, not the server-rendered prop, so they stay
  // accurate after a nudge mutates state.
  const statePills = (() => {
    const counts: Record<string, number> = {};
    for (const inv of invoices) {
      const key = inv.state.toLowerCase();
      counts[key] = (counts[key] || 0) + 1;
    }
    return [
      { value: "ALL", label: "ALL", count: invoices.length },
      ...Object.entries(counts)
        .sort(([, a], [, b]) => b - a)
        .map(([value, count]) => ({ value, label: STATE_LABELS[value] || value, count })),
    ];
  })();

  const edgePills = (() => {
    const counts: Record<string, number> = {};
    for (const inv of invoices) {
      if (inv.edge_case && inv.edge_case !== "none") {
        counts[inv.edge_case] = (counts[inv.edge_case] || 0) + 1;
      }
    }
    return Object.entries(counts)
      .sort(([, a], [, b]) => b - a)
      .map(([value, count]) => {
        const meta = edgeCaseMeta(value);
        return { value, label: meta.label, title: meta.title, count };
      });
  })();

  const totalOutstanding = filtered.reduce((sum, inv) => sum + Number(inv.outstanding_amount), 0);

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div className="relative flex-1 max-w-md">
          <svg
            className="absolute left-3.5 top-3 h-4 w-4 text-slate-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
            />
          </svg>
          <input
            id="invoice-search-input"
            type="text"
            placeholder="Search by company, contact, or invoice #..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            aria-label="Search invoices by buyer company, contact name, invoice number, or ID"
            className="glass-input w-full rounded-2xl pl-10 pr-4 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none"
          />
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs font-bold text-slate-400">State:</span>
          {statePills.map((pill) => (
            <button
              key={pill.value}
              type="button"
              onClick={() => setStatusFilter(pill.value)}
              aria-pressed={statusFilter === pill.value}
              className={`rounded-xl px-3 py-1.5 text-[11px] font-bold transition-all ${
                statusFilter === pill.value
                  ? "bg-gradient-to-r from-sky-500 to-blue-600 text-white shadow-md shadow-sky-500/25"
                  : "glass-card border-white/[0.08] text-slate-400 hover:border-white/[0.2] hover:text-white"
              }`}
            >
              {pill.label}{" "}
              <span className="ml-1 font-mono font-medium opacity-60">{pill.count}</span>
            </button>
          ))}
        </div>
      </div>

      {edgePills.length > 0 ? (
        <div className="flex flex-wrap items-center gap-2">
          <span
            className="cursor-help text-xs font-bold text-slate-400"
            title="Adversarial scenarios planted by the data generator. Each tests a specific policy guardrail."
          >
            Edge Case:
          </span>
          <button
            type="button"
            onClick={() => setEdgeFilter("ALL")}
            aria-pressed={edgeFilter === "ALL"}
            className={`rounded-xl px-3 py-1.5 text-[11px] font-bold transition-all ${
              edgeFilter === "ALL"
                ? "bg-gradient-to-r from-violet-500 to-fuchsia-600 text-white shadow-md shadow-violet-500/25"
                : "glass-card border-white/[0.08] text-slate-400 hover:border-white/[0.2] hover:text-white"
            }`}
          >
            ALL
          </button>
          {edgePills.map((pill) => (
            <button
              key={pill.value}
              type="button"
              title={pill.title}
              onClick={() => setEdgeFilter(pill.value)}
              aria-pressed={edgeFilter === pill.value}
              className={`rounded-xl px-3 py-1.5 text-[11px] font-bold transition-all ${
                edgeFilter === pill.value
                  ? "bg-gradient-to-r from-violet-500 to-fuchsia-600 text-white shadow-md shadow-violet-500/25"
                  : "glass-card border-white/[0.08] text-slate-400 hover:border-white/[0.2] hover:text-white"
              }`}
            >
              {pill.label}{" "}
              <span className="ml-1 font-mono font-medium opacity-60">{pill.count}</span>
            </button>
          ))}
        </div>
      ) : null}

      <div className="flex flex-wrap items-center gap-3 text-[11px] text-slate-400">
        <span>
          Showing <span className="font-bold text-white">{filtered.length}</span> of{" "}
          {invoices.length} invoices
        </span>
        <span className="text-slate-600">|</span>
        <span>
          Outstanding in view:{" "}
          <span className="font-mono font-bold text-amber-300">{formatINR(totalOutstanding)}</span>
        </span>
      </div>

      <div className="glass-panel overflow-hidden rounded-3xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="border-b border-white/[0.08] bg-slate-900/80 font-bold uppercase tracking-wider text-slate-400">
              <tr>
                <th className="px-4 py-3.5">Invoice #</th>
                <th className="px-4 py-3.5">Buyer</th>
                <th className="px-4 py-3.5">Amount / Outstanding</th>
                <th className="px-4 py-3.5">Due</th>
                <th className="px-4 py-3.5">Ageing</th>
                <th className="px-4 py-3.5">Risk</th>
                <th className="px-4 py-3.5">State</th>
                <th className="px-4 py-3.5 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={8} className="px-4 py-8 text-center text-slate-500">
                    No matching invoices found.
                  </td>
                </tr>
              ) : (
                filtered.map((inv) => {
                  const total = Number(inv.total_amount);
                  const outstanding = Number(inv.outstanding_amount);
                  const isPartial = outstanding > 0 && outstanding < total;
                  const isSettled = outstanding === 0;

                  return (
                    <tr key={inv.invoice_id} className="transition-colors hover:bg-slate-800/40">
                      <td className="px-4 py-3.5 font-semibold">
                        <a
                          href={`/invoices/${inv.invoice_id}`}
                          className="text-sky-400 hover:underline"
                        >
                          {inv.invoice_number}
                        </a>
                      </td>

                      <td className="px-4 py-3.5">
                        <a href={`/buyers/${inv.buyer_id}`} className="group block">
                          <span className="font-semibold text-white group-hover:underline">
                            {inv.buyer_company_name}
                          </span>
                          <span className="mt-0.5 block text-[10px] text-slate-400">
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
                          <span className="mt-0.5 block text-[10px] font-bold uppercase text-emerald-400">
                            Settled
                          </span>
                        ) : isPartial ? (
                          <span
                            className="mt-0.5 block font-mono text-[10px] font-bold text-amber-300"
                            title={`${formatINR(inv.amount_paid)} already paid`}
                          >
                            {formatINR(outstanding)} outstanding
                          </span>
                        ) : (
                          <span className="mt-0.5 block font-mono text-[10px] text-slate-500">
                            nothing paid
                          </span>
                        )}
                      </td>

                      <td className="whitespace-nowrap px-4 py-3.5 text-slate-300">
                        {formatDateShort(inv.due_date)}
                      </td>

                      <td className="whitespace-nowrap px-4 py-3.5">
                        {isSettled && inv.paid_date ? (
                          <span className="block">
                            <span className="font-semibold text-emerald-400">
                              Paid {formatDateShort(inv.paid_date)}
                            </span>
                            <span className="mt-0.5 block text-[10px] text-slate-400">
                              {inv.days_late > 0 ? `${inv.days_late}d late` : "on time"}
                            </span>
                          </span>
                        ) : inv.days_overdue > 0 ? (
                          <span
                            className={`font-semibold ${
                              inv.days_overdue > 60
                                ? "text-rose-400"
                                : inv.days_overdue > 30
                                  ? "text-amber-400"
                                  : "text-sky-400"
                            }`}
                          >
                            {inv.days_overdue} days overdue
                          </span>
                        ) : (
                          <span className="text-slate-500">Not yet due</span>
                        )}
                      </td>

                      <td className="px-4 py-3.5">
                        <span
                          className={`inline-flex rounded-full border px-2.5 py-0.5 text-[10px] font-extrabold uppercase ${getRiskBadge(inv.risk_tier)}`}
                        >
                          {inv.risk_tier}
                        </span>
                      </td>

                      <td className="px-4 py-3.5">
                        <span
                          className={`inline-flex rounded-md border px-2 py-0.5 text-[10px] font-bold uppercase ${getStateBadge(inv.state)}`}
                        >
                          {inv.state.replace(/_/g, " ")}
                        </span>
                        {inv.edge_case && inv.edge_case !== "none" ? (
                          <span className="mt-1 block">
                            <EdgeCaseBadge edgeCase={inv.edge_case} />
                          </span>
                        ) : null}
                      </td>

                      <td className="px-4 py-3.5 text-right">
                        <button
                          type="button"
                          onClick={() => setActiveNudgeId(inv.invoice_id)}
                          aria-label={`Preview nudge template for invoice ${inv.invoice_number}`}
                          className="rounded-lg border border-sky-500/20 bg-sky-500/10 px-2.5 py-1 text-[11px] font-bold text-sky-400 shadow-sm transition-all hover:bg-sky-500 hover:text-white"
                        >
                          Nudge Preview
                        </button>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      <NudgeModal
        invoiceId={activeNudgeId}
        onClose={() => setActiveNudgeId(null)}
        onSuccess={() => {
          setActiveNudgeId(null);
          refreshInvoices();
        }}
      />
    </div>
  );
}

export default InvoiceTableInteractive;
