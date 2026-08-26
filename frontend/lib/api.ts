import type {
  AuditRow,
  BaselineRow,
  BuyerRow,
  Envelope,
  InboxRow,
  InvoiceDetail,
  InvoiceRow,
  NudgePreview,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  });
  const body: unknown = await response.json();
  if (!response.ok) {
    const err = body as { error?: { message?: string } };
    throw new Error(err.error?.message ?? `Request failed: ${response.status}`);
  }
  return body as T;
}

export async function listInvoices(params?: {
  status?: string;
  risk_tier?: string;
}): Promise<Envelope<InvoiceRow[]>> {
  const query = new URLSearchParams();
  query.set("limit", "100");
  if (params?.status) query.set("status", params.status);
  if (params?.risk_tier) query.set("risk_tier", params.risk_tier);
  return request<Envelope<InvoiceRow[]>>(`/api/invoices?${query.toString()}`);
}

export async function getInvoice(id: string): Promise<Envelope<InvoiceDetail>> {
  return request<Envelope<InvoiceDetail>>(`/api/invoices/${id}`);
}

export async function listBuyers(): Promise<Envelope<BuyerRow[]>> {
  return request<Envelope<BuyerRow[]>>("/api/buyers?limit=100");
}

export async function getBuyer(id: string): Promise<Envelope<BuyerRow & { invoices: Array<{ invoice_id: string; invoice_number: string; total_amount: string; amount_paid: string; outstanding_amount: string; due_date: string; status: string; state: string; days_overdue: number }> }>> {
  return request(`/api/buyers/${id}`);
}

export async function getBuyerBrief(buyerId: string): Promise<Envelope<import("./types").BuyerBrief>> {
  return request<Envelope<import("./types").BuyerBrief>>(`/api/buyers/${buyerId}/brief`);
}

export async function listAudit(
  paramsOrInvoiceId?:
    | string
    | {
        invoice_id?: string;
        actor?: string;
        from_state?: string;
        to_state?: string;
        limit?: number;
        offset?: number;
      }
): Promise<Envelope<AuditRow[]>> {
  const query = new URLSearchParams();
  if (typeof paramsOrInvoiceId === "string") {
    query.set("invoice_id", paramsOrInvoiceId);
    query.set("limit", "100");
  } else if (paramsOrInvoiceId) {
    query.set("limit", String(paramsOrInvoiceId.limit ?? 200));
    if (paramsOrInvoiceId.offset !== undefined) query.set("offset", String(paramsOrInvoiceId.offset));
    if (paramsOrInvoiceId.invoice_id) query.set("invoice_id", paramsOrInvoiceId.invoice_id);
    if (paramsOrInvoiceId.actor) query.set("actor", paramsOrInvoiceId.actor);
    if (paramsOrInvoiceId.from_state) query.set("from_state", paramsOrInvoiceId.from_state);
    if (paramsOrInvoiceId.to_state) query.set("to_state", paramsOrInvoiceId.to_state);
  } else {
    query.set("limit", "200");
  }
  return request<Envelope<AuditRow[]>>(`/api/audit?${query.toString()}`);
}

export async function verifyAudit(): Promise<Envelope<import("./types").AuditVerification>> {
  return request<Envelope<import("./types").AuditVerification>>("/api/audit/verify");
}

export async function listBaselines(): Promise<Envelope<BaselineRow[]>> {
  return request<Envelope<BaselineRow[]>>("/api/metrics/baseline");
}

export async function listInbox(): Promise<Envelope<InboxRow[]>> {
  return request<Envelope<InboxRow[]>>("/api/inbox");
}

export async function previewNudge(invoiceId: string): Promise<Envelope<NudgePreview>> {
  return request<Envelope<NudgePreview>>(`/api/nudge/preview/${invoiceId}`);
}

export async function triggerNudge(
  invoiceId: string,
  dryRun: boolean,
): Promise<Envelope<{ sent: boolean; new_state: string | null; preview: NudgePreview }>> {
  return request(`/api/nudge/trigger?dry_run=${dryRun ? "true" : "false"}`, {
    method: "POST",
    body: JSON.stringify({ invoice_id: invoiceId }),
  });
}

export async function injectReply(invoiceId: string, text: string): Promise<Envelope<{ state: string }>> {
  return request("/api/inbox/reply", {
    method: "POST",
    body: JSON.stringify({ invoice_id: invoiceId, text }),
  });
}

export async function seedDemo(): Promise<Envelope<Record<string, number>>> {
  return request("/api/seed?num_invoices=80&seed=42", { method: "POST" });
}

export async function askAssistant(params: {
  query: string;
  buyer_id?: string;
  invoice_id?: string;
}): Promise<Envelope<import("./types").AssistantResponse>> {
  return request<Envelope<import("./types").AssistantResponse>>("/api/assistant/ask", {
    method: "POST",
    body: JSON.stringify(params),
  });
}
