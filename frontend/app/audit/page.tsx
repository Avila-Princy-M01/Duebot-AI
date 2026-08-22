import { AuditLog } from "../../components/audit/AuditLog";
import { listAudit } from "../../lib/api";

export default async function AuditPage() {
  const payload = await listAudit();
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-extrabold tracking-tight text-white">Append-Only Policy Audit Log</h1>
        <p className="text-xs text-slate-400">
          Immutable audit record of every DueBot state transition, WhatsApp nudge, and human review routing.
        </p>
      </div>
      <AuditLog rows={payload.data} />
    </div>
  );
}
