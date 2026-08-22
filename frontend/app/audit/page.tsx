import { AuditLog } from "../../components/audit/AuditLog";
import { listAudit } from "../../lib/api";

export async function AuditPage() {
  const payload = await listAudit();
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Append-only audit log</h1>
      <p className="text-sm text-slate-400">
        There is no edit or delete. Every state transition is one row with a human-readable reason.
      </p>
      <AuditLog rows={payload.data} />
    </div>
  );
}

export default AuditPage;
