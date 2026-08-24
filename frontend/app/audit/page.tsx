"use client";

import { useEffect, useState } from "react";
import { AuditLog } from "../../components/audit/AuditLog";
import { listAudit } from "../../lib/api";
import type { AuditRow } from "../../lib/types";

export default function AuditPage() {
  const [rows, setRows] = useState<AuditRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadAudit = () => {
    setLoading(true);
    void listAudit()
      .then((res) => {
        setRows(res.data);
        setError(null);
      })
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : "Failed to load audit logs");
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadAudit();
    const interval = setInterval(loadAudit, 3000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-2xl font-extrabold tracking-tight text-white">Append-Only Policy Audit Log</h1>
          <p className="text-xs text-slate-400">
            Immutable audit record of every DueBot state transition, WhatsApp nudge, and human review routing.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={loadAudit}
            className="flex items-center gap-1.5 rounded-xl border border-slate-800 bg-panel px-3 py-1.5 text-xs font-semibold text-slate-300 hover:bg-slate-800 hover:text-white transition-all shadow-sm"
          >
            <span className={`h-2 w-2 rounded-full ${loading ? "bg-amber-400 animate-ping" : "bg-emerald-400"}`} />
            <span>{loading ? "Refreshing..." : "Refresh Live"}</span>
          </button>
          <span className="rounded-xl border border-slate-800 bg-panel px-3 py-1.5 text-xs font-bold text-sky-400">
            {rows.length} Total Transitions Logged
          </span>
        </div>
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
