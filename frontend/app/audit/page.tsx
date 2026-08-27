import { AuditInteractive } from "../../components/audit/AuditInteractive";
import { listAudit, verifyAudit } from "../../lib/api";
import type { AuditRow, AuditVerification } from "../../lib/types";

export default async function AuditPage() {
  let initialRows: AuditRow[] = [];
  let initialTotalCount = 0;
  let initialVerification: AuditVerification | null = null;
  let error: string | null = null;

  try {
    const [auditRes, verifyRes] = await Promise.all([
      listAudit({ limit: 50, offset: 0 }),
      verifyAudit().catch(() => null),
    ]);
    initialRows = auditRes.data ?? [];
    initialTotalCount = auditRes.meta?.total_count ?? initialRows.length;
    if (verifyRes) initialVerification = verifyRes.data ?? null;
  } catch (exc) {
    error = exc instanceof Error ? exc.message : "Failed to load audit logs";
  }

  if (error) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-extrabold tracking-tight text-white">Append-Only Policy Audit Log</h1>
        </div>
        <div className="rounded-2xl border border-rose-500/40 bg-rose-950/30 p-5 text-xs text-rose-200 backdrop-blur-md" role="alert">
          <p className="font-bold">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <AuditInteractive
      initialRows={initialRows}
      initialTotalCount={initialTotalCount}
      initialVerification={initialVerification}
    />
  );
}
