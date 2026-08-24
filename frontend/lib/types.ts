export interface Envelope<T> {
  data: T;
  meta: {
    timestamp: string;
    request_id: string;
    total_count: number | null;
  };
}

export interface InvoiceRow {
  invoice_id: string;
  merchant_id: string;
  buyer_id: string;
  invoice_number: string;
  issue_date: string;
  due_date: string;
  total_amount: string;
  amount_paid: string;
  currency: string;
  status: string;
  state: string;
  days_overdue: number;
  risk_tier: string;
  opted_out: boolean;
  split: string;
  edge_case: string;
  payment_link_id: string | null;
}

export interface InteractionRow {
  id: string;
  channel: string;
  direction: string;
  sent_at: string;
  message_text: string;
  intent_label: string;
  confidence: number | null;
  delivery_status: string;
  attempt_number: number;
}

export interface AuditRow {
  id: string;
  invoice_id?: string;
  from_state: string;
  to_state: string;
  actor: string;
  occurred_at: string;
  reasoning_summary: string;
  extra_metadata: Record<string, unknown> | null;
}

export interface InvoiceDetail extends InvoiceRow {
  subtotal_amount: string;
  gst_rate: number;
  gst_amount: string;
  payment_terms_days: number;
  notes: string | null;
  would_have_paid_without_intervention: boolean | null;
  promise_outcome: string;
  interactions: InteractionRow[];
  promises: Array<{
    id: string;
    promised_date: string;
    promised_amount: string | null;
    confidence: number;
    status: string;
  }>;
  audit: AuditRow[];
}

export interface BuyerRow {
  buyer_id: string;
  merchant_id: string;
  company_name: string;
  contact_name: string;
  reliability_tier: string;
  on_time_payment_rate: number;
  relationship_since: string;
}

export interface BaselineRow {
  id: string;
  run_id: string;
  strategy: string;
  eval_set_size: number;
  recovered_count: number;
  recovered_value: string;
  total_value: string;
  avg_days_to_recovery: number;
  recovery_30d: number;
  recovery_60d: number;
  recovery_90d: number;
  total_contacts_sent: number;
  created_at: string;
}

export interface InboxRow {
  interaction_id: string;
  invoice_id: string;
  to_phone_masked: string;
  body: string;
  sent_at: string;
  direction: string;
}

export interface NudgePreview {
  invoice_id: string;
  allowed: boolean;
  policy_reason: string;
  approaching_cap: boolean;
  contacts_this_week: number;
  drafted_message: string;
  channel: string;
  next_action_at: string | null;
  current_state: string;
  target_event: string;
}

export interface BuyerBrief {
  buyer_id: string;
  company_name: string;
  contact_name: string;
  summary: string;
  spoken_summary: string;
  risk_assessment: string;
  recommended_action: string;
  total_outstanding_inr: string;
  open_invoices_count: number;
  model: string;
}

export interface AssistantResponse {
  answer: string;
  spoken_answer: string;
  category: string;
  suggested_action: string | null;
  model: string;
}


