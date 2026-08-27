import { InboxInteractive } from "../../components/inbox/InboxInteractive";
import { listInbox } from "../../lib/api";
import type { InboxRow } from "../../lib/types";

export default async function InboxPage() {
  let initialRows: InboxRow[] = [];
  let error: string | null = null;

  try {
    const payload = await listInbox();
    initialRows = payload?.data ?? [];
  } catch (exc) {
    error = exc instanceof Error ? exc.message : "Failed to load inbox";
  }

  if (error) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-extrabold tracking-tight text-white">WhatsApp Communication Inbox</h1>
        <div className="rounded-2xl border border-rose-500/40 bg-rose-950/30 p-5 text-xs text-rose-200 backdrop-blur-md" role="alert">
          <p className="font-bold">{error}</p>
        </div>
      </div>
    );
  }

  return <InboxInteractive initialRows={initialRows} />;
}
