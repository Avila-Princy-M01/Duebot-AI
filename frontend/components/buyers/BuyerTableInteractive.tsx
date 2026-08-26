"use client";

import { useState } from "react";
import type { BuyerRow } from "../../lib/types";
import { SeedButton } from "../ui/SeedButton";

interface BuyerTableInteractiveProps {
  buyers: BuyerRow[];
}

export function BuyerTableInteractive({ buyers }: BuyerTableInteractiveProps) {
  const [search, setSearch] = useState("");
  const [tierFilter, setTierFilter] = useState("ALL");

  /* Map filter keys to actual backend reliability_tier values */
  const tierOptions: { key: string; label: string; value: string }[] = [
    { key: "ALL", label: "ALL", value: "ALL" },
    { key: "reliable", label: "Reliable", value: "reliable" },
    { key: "occasional_late", label: "Occasional Late", value: "occasional_late" },
    { key: "chronic_late", label: "Chronic Late", value: "chronic_late" },
  ];

  const filtered = buyers.filter((b) => {
    const needle = search.toLowerCase().trim();
    const matchesSearch =
      needle === "" ||
      b.company_name.toLowerCase().includes(needle) ||
      b.contact_name.toLowerCase().includes(needle) ||
      b.buyer_id.toLowerCase().includes(needle);

    const matchesTier =
      tierFilter === "ALL" ||
      b.reliability_tier.toLowerCase() === tierFilter.toLowerCase();
    return matchesSearch && matchesTier;
  });

  const getTierBadge = (tier: string) => {
    switch (tier.toLowerCase()) {
      case "reliable":
        return "bg-emerald-500/10 text-emerald-400 border-emerald-500/30";
      case "occasional_late":
        return "bg-amber-500/10 text-amber-400 border-amber-500/30";
      case "chronic_late":
        return "bg-rose-500/10 text-rose-400 border-rose-500/30";
      default:
        return "bg-purple-500/10 text-purple-400 border-purple-500/30";
    }
  };

  const getTierLabel = (tier: string) => {
    switch (tier.toLowerCase()) {
      case "reliable":
        return "Reliable";
      case "occasional_late":
        return "Occasional Late";
      case "chronic_late":
        return "Chronic Late";
      default:
        return tier;
    }
  };

  const hasActiveFilters = search.trim() !== "" || tierFilter !== "ALL";

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div className="relative flex-1 max-w-md">
          <svg className="absolute left-3.5 top-3 h-4 w-4 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            id="buyer-search-input"
            type="text"
            placeholder="Search company or contact..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            aria-label="Search buyers by company or contact name"
            className="glass-input w-full rounded-2xl pl-10 pr-4 py-2 text-xs text-white placeholder-slate-500 focus:outline-none"
          />
        </div>

        <div className="flex flex-wrap items-center gap-2" role="group" aria-label="Filter buyers by reliability tier">
          <span className="text-xs font-bold text-slate-400">Reliability:</span>
          {tierOptions.map((t) => (
            <button
              key={t.key}
              type="button"
              onClick={() => setTierFilter(t.value)}
              aria-pressed={tierFilter === t.value}
              className={`rounded-xl px-3 py-1.5 text-xs font-bold transition-all ${
                tierFilter === t.value
                  ? "bg-gradient-to-r from-sky-500 to-blue-600 text-white shadow-md shadow-sky-500/25"
                  : "glass-card border-white/[0.08] text-slate-400 hover:border-white/[0.2] hover:text-white"
              }`}
            >
              {t.label}
            </button>
          ))}

          {hasActiveFilters && (
            <button
              type="button"
              onClick={() => {
                setSearch("");
                setTierFilter("ALL");
              }}
              className="rounded-xl border border-rose-500/30 bg-rose-500/10 px-3 py-1.5 text-xs font-semibold text-rose-300 hover:bg-rose-500/20 transition-all"
            >
              Clear Filters
            </button>
          )}
        </div>
      </div>

      <div className="glass-panel overflow-hidden rounded-3xl border border-white/[0.08]">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="border-b border-white/[0.08] bg-slate-900/90 text-slate-300 font-bold uppercase tracking-wider">
              <tr>
                <th className="px-4 py-3.5">Company Name</th>
                <th className="px-4 py-3.5">Contact Person</th>
                <th className="px-4 py-3.5">Buyer ID</th>
                <th className="px-4 py-3.5">Reliability Tier</th>
                <th className="px-4 py-3.5">On-Time Pay Rate</th>
                <th className="px-4 py-3.5 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.06] font-sans">
              {buyers.length === 0 ? (
                /* Empty State 1: Database not seeded */
                <tr>
                  <td colSpan={6} className="px-4 py-12 text-center">
                    <div className="max-w-md mx-auto space-y-3">
                      <div className="h-12 w-12 rounded-2xl bg-slate-800 border border-slate-700 mx-auto flex items-center justify-center text-slate-400">
                        <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                        </svg>
                      </div>
                      <h4 className="text-sm font-bold text-white">No Buyers Loaded</h4>
                      <p className="text-xs text-slate-400">
                        The buyer directory is empty. Seed synthetic invoices to populate realistic customer profiles and historical payment histories.
                      </p>
                      <div className="pt-2 flex justify-center">
                        <SeedButton />
                      </div>
                    </div>
                  </td>
                </tr>
              ) : filtered.length === 0 ? (
                /* Empty State 2: Filters yielded 0 matches */
                <tr>
                  <td colSpan={6} className="px-4 py-10 text-center">
                    <div className="space-y-2">
                      <p className="text-xs text-slate-300 font-semibold">
                        No buyers match the active search and filter criteria.
                      </p>
                      <button
                        type="button"
                        onClick={() => {
                          setSearch("");
                          setTierFilter("ALL");
                        }}
                        className="mt-1 inline-flex items-center gap-1 rounded-xl border border-sky-500/30 bg-sky-500/10 px-3 py-1.5 text-xs font-bold text-sky-400 hover:bg-sky-500 hover:text-white transition-all"
                      >
                        Reset Filters (Show All {buyers.length} Buyers)
                      </button>
                    </div>
                  </td>
                </tr>
              ) : (
                filtered.map((buyer) => {
                  const ratePct = Math.round((buyer.on_time_payment_rate ?? 0) * 100);
                  return (
                    <tr key={buyer.buyer_id} className="transition-colors hover:bg-white/[0.03]">
                      <td className="px-4 py-3.5 font-bold text-white">
                        <a href={`/buyers/${buyer.buyer_id}`} className="text-sky-400 hover:underline">
                          {buyer.company_name}
                        </a>
                      </td>
                      <td className="px-4 py-3.5 text-slate-300 font-medium">{buyer.contact_name}</td>
                      <td className="px-4 py-3.5 font-mono text-xs text-slate-400">
                        {buyer.buyer_id}
                      </td>
                      <td className="px-4 py-3.5">
                        <span className={`inline-flex rounded-full border px-2.5 py-0.5 text-xs font-extrabold uppercase ${getTierBadge(buyer.reliability_tier)}`}>
                          {getTierLabel(buyer.reliability_tier)}
                        </span>
                      </td>
                      <td className="px-4 py-3.5">
                        <div className="flex items-center gap-2">
                          <div className="h-1.5 w-20 overflow-hidden rounded-full bg-slate-800">
                            <div
                              className={`h-full rounded-full ${ratePct > 80 ? "bg-emerald-400" : ratePct > 50 ? "bg-sky-400" : "bg-rose-400"}`}
                              style={{ width: `${ratePct}%` }}
                            />
                          </div>
                          <span className="font-mono font-bold text-white">{ratePct}%</span>
                        </div>
                      </td>
                      <td className="px-4 py-3.5 text-right">
                        <a
                          href={`/buyers/${buyer.buyer_id}`}
                          className="inline-flex items-center gap-1 rounded-xl border border-sky-500/30 bg-sky-500/10 px-3 py-1.5 text-xs font-bold text-sky-300 hover:bg-sky-500 hover:text-white transition-all shadow-sm"
                        >
                          Profile & Invoices →
                        </a>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

export default BuyerTableInteractive;
