"use client";

import { useState } from "react";
import type { BuyerRow } from "../../lib/types";

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
    const matchesSearch =
      search === "" ||
      b.company_name.toLowerCase().includes(search.toLowerCase()) ||
      b.contact_name.toLowerCase().includes(search.toLowerCase()) ||
      b.buyer_id.toLowerCase().includes(search.toLowerCase());

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
            className="w-full rounded-xl border border-slate-800 bg-panel/80 pl-10 pr-4 py-2 text-xs text-white placeholder-slate-500 focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500"
          />
        </div>

        <div className="flex items-center gap-2" role="group" aria-label="Filter buyers by reliability tier">
          <span className="text-xs font-semibold text-slate-400">Reliability:</span>
          {tierOptions.map((t) => (
            <button
              key={t.key}
              type="button"
              onClick={() => setTierFilter(t.value)}
              aria-pressed={tierFilter === t.value}
              className={`rounded-lg px-2.5 py-1 text-[11px] font-bold transition-all ${
                tierFilter === t.value
                  ? "bg-sky-500 text-white shadow-sm shadow-sky-500/20"
                  : "bg-panel border border-slate-800 text-slate-400 hover:bg-slate-800 hover:text-slate-200"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      <div className="overflow-hidden rounded-2xl border border-slate-800/80 bg-panel/60 backdrop-blur-md shadow-xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="border-b border-slate-800 bg-panel/90 text-slate-400 font-bold uppercase tracking-wider">
              <tr>
                <th className="px-4 py-3.5">Company Name</th>
                <th className="px-4 py-3.5">Contact Person</th>
                <th className="px-4 py-3.5">Buyer ID</th>
                <th className="px-4 py-3.5">Reliability Tier</th>
                <th className="px-4 py-3.5">On-Time Pay Rate</th>
                <th className="px-4 py-3.5 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-slate-500">
                    No buyers found.
                  </td>
                </tr>
              ) : (
                filtered.map((buyer) => {
                  const ratePct = Math.round((buyer.on_time_payment_rate ?? 0) * 100);
                  return (
                    <tr key={buyer.buyer_id} className="transition-colors hover:bg-slate-800/40">
                      <td className="px-4 py-3.5 font-bold text-white">
                        <a href={`/buyers/${buyer.buyer_id}`} className="text-sky-400 hover:underline">
                          {buyer.company_name}
                        </a>
                      </td>
                      <td className="px-4 py-3.5 text-slate-300 font-medium">{buyer.contact_name}</td>
                      <td className="px-4 py-3.5 font-mono text-[11px] text-slate-400">
                        {buyer.buyer_id}
                      </td>
                      <td className="px-4 py-3.5">
                        <span className={`inline-flex rounded-full border px-2.5 py-0.5 text-[10px] font-extrabold uppercase ${getTierBadge(buyer.reliability_tier)}`}>
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
                          className="inline-flex items-center gap-1 rounded-lg border border-sky-500/30 bg-sky-500/10 px-3 py-1.5 text-xs font-bold text-sky-400 hover:bg-sky-500 hover:text-white transition-all shadow-sm"
                        >
                          🎙️ Brief →
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
