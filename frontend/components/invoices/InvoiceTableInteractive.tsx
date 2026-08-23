"use client";

import { useState } from "react";
import type { InvoiceRow } from "../../lib/types";
import { NudgeModal } from "./NudgeModal";

interface InvoiceTableInteractiveProps {
  initialInvoices: InvoiceRow[];
}

export function InvoiceTableInteractive({ initialInvoices }: InvoiceTableInteractiveProps) {
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [riskFilter, setRiskFilter] = useState<string>("ALL");
  const [activeNudgeId, setActiveNudgeId] = useState<string | null>(null);

  const filtered = initialInvoices.filter((inv) => {
    const matchesSearch =
      search === "" ||
      inv.invoice_number.toLowerCase().includes(search.toLowerCase()) ||
      inv.buyer_id.toLowerCase().includes(search.toLowerCase()) ||
      inv.invoice_id.toLowerCase().includes(search.toLowerCase());

    const matchesStatus =
      statusFilter === "ALL" ||
      inv.status.toLowerCase() === statusFilter.toLowerCase() ||
      inv.state.toLowerCase() === statusFilter.toLowerCase();

    const matchesRisk =
      riskFilter === "ALL" || inv.risk_tier.toLowerCase() === riskFilter.toLowerCase();

    return matchesSearch && matchesStatus && matchesRisk;
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
      case "promise_active":
      case "promise_kept":
        return "bg-emerald-500/10 text-emerald-400 border-emerald-500/20";
      case "human_review":
        return "bg-amber-500/10 text-amber-400 border-amber-500/20 animate-pulse";
      case "escalated":
        return "bg-purple-500/10 text-purple-400 border-purple-500/20";
      default:
        return "bg-slate-800 text-slate-400 border-slate-700";
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div className="relative flex-1 max-w-md">
          <svg className="absolute left-3.5 top-3 h-4 w-4 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            type="text"
            placeholder="Search by invoice # or ID..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full rounded-xl border border-slate-800 bg-panel/80 pl-10 pr-4 py-2 text-xs text-white placeholder-slate-500 focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500"
          />
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs font-semibold text-slate-400">State:</span>
          {[
            { value: "ALL", label: "ALL" },
            { value: "created", label: "Created" },
            { value: "overdue", label: "Overdue" },
            { value: "nudged", label: "Nudged" },
            { value: "replied", label: "Replied" },
            { value: "promised", label: "Promised" },
            { value: "reminded", label: "Reminded" },
            { value: "recovered", label: "Recovered" },
            { value: "disputed", label: "Disputed" },
            { value: "escalated", label: "Escalated" },
            { value: "human_review", label: "Human Review" },
            { value: "opted_out", label: "Opted Out" },
            { value: "terminated", label: "Terminated" },
          ].map((st) => (
            <button
              key={st.value}
              type="button"
              onClick={() => setStatusFilter(st.value)}
              className={`rounded-lg px-2.5 py-1 text-[11px] font-bold transition-all ${
                statusFilter === st.value
                  ? "bg-sky-500 text-white shadow-sm shadow-sky-500/20"
                  : "bg-panel border border-slate-800 text-slate-400 hover:bg-slate-800 hover:text-slate-200"
              }`}
            >
              {st.label}
            </button>
          ))}
        </div>
      </div>

      <div className="overflow-hidden rounded-2xl border border-slate-800/80 bg-panel/60 backdrop-blur-md shadow-xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="border-b border-slate-800 bg-panel/90 text-slate-400 font-bold uppercase tracking-wider">
              <tr>
                <th className="px-4 py-3.5">Invoice #</th>
                <th className="px-4 py-3.5">Buyer</th>
                <th className="px-4 py-3.5">Total Amount</th>
                <th className="px-4 py-3.5">Days Overdue</th>
                <th className="px-4 py-3.5">Risk Tier</th>
                <th className="px-4 py-3.5">State</th>
                <th className="px-4 py-3.5 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-slate-500">
                    No matching invoices found.
                  </td>
                </tr>
              ) : (
                filtered.map((inv) => (
                  <tr key={inv.invoice_id} className="transition-colors hover:bg-slate-800/40">
                    <td className="px-4 py-3.5 font-semibold text-white">
                      <a href={`/invoices/${inv.invoice_id}`} className="text-sky-400 hover:underline">
                        {inv.invoice_number}
                      </a>
                    </td>
                    <td className="px-4 py-3.5 text-slate-300">
                      <a href={`/buyers/${inv.buyer_id}`} className="hover:text-white hover:underline">
                        {inv.buyer_id}
                      </a>
                    </td>
                    <td className="px-4 py-3.5 font-mono font-bold text-white">
                      ₹{Number(inv.total_amount).toLocaleString("en-IN")}
                    </td>
                    <td className="px-4 py-3.5">
                      <span className={`font-semibold ${inv.days_overdue > 60 ? "text-rose-400" : inv.days_overdue > 30 ? "text-amber-400" : "text-sky-400"}`}>
                        {inv.days_overdue} days
                      </span>
                    </td>
                    <td className="px-4 py-3.5">
                      <span className={`inline-flex rounded-full border px-2.5 py-0.5 text-[10px] font-extrabold uppercase ${getRiskBadge(inv.risk_tier)}`}>
                        {inv.risk_tier}
                      </span>
                    </td>
                    <td className="px-4 py-3.5">
                      <span className={`inline-flex rounded-md border px-2 py-0.5 text-[10px] font-bold uppercase ${getStateBadge(inv.state)}`}>
                        {inv.state.replace("_", " ")}
                      </span>
                    </td>
                    <td className="px-4 py-3.5 text-right">
                      <button
                        type="button"
                        onClick={() => setActiveNudgeId(inv.invoice_id)}
                        className="rounded-lg bg-sky-500/10 px-2.5 py-1 text-[11px] font-bold text-sky-400 border border-sky-500/20 hover:bg-sky-500 hover:text-white transition-all shadow-sm"
                      >
                        Nudge Preview →
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      <NudgeModal
        invoiceId={activeNudgeId}
        onClose={() => setActiveNudgeId(null)}
        onSuccess={() => setActiveNudgeId(null)}
      />
    </div>
  );
}

export default InvoiceTableInteractive;
