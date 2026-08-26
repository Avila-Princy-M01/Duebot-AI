"""Initial DueBot schema (ARCHITECTURE.md §15).

audit_log is append-only from application code: there are no UPDATE or DELETE
repositories. On Postgres, also run (as a superuser, after creating app_role):

    REVOKE UPDATE, DELETE ON audit_log FROM app_role;

Local SQLite/dev databases may not have app_role; the ORM still never issues
UPDATE/DELETE against this table.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create merchants, buyers, invoices, interactions, promises, audit_log, baseline."""
    op.create_table(
        "merchants",
        sa.Column("merchant_id", sa.String(20), primary_key=True),
        sa.Column("business_name", sa.String(255), nullable=False),
        sa.Column("business_type", sa.String(50), nullable=False),
        sa.Column("gstin", sa.String(15), nullable=False, unique=True),
        sa.Column("city", sa.String(100), nullable=False),
        sa.Column("state_code", sa.String(2), nullable=False),
        sa.Column("onboarded_date", sa.Date(), nullable=False),
    )
    op.create_table(
        "buyers",
        sa.Column("buyer_id", sa.String(30), primary_key=True),
        sa.Column("merchant_id", sa.String(20), sa.ForeignKey("merchants.merchant_id"), nullable=False),
        sa.Column("company_name", sa.String(255), nullable=False),
        sa.Column("contact_name", sa.String(255), nullable=False),
        sa.Column("phone", sa.String(20), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("gstin", sa.String(15), nullable=False),
        sa.Column("reliability_tier", sa.String(20), nullable=False),
        sa.Column("on_time_payment_rate", sa.Float(), nullable=False),
        sa.Column("relationship_since", sa.Date(), nullable=False),
        sa.CheckConstraint(
            "reliability_tier IN ('reliable', 'occasional_late', 'chronic_late')",
            name="ck_buyers_reliability_tier",
        ),
        sa.CheckConstraint(
            "on_time_payment_rate >= 0.0 AND on_time_payment_rate <= 1.0",
            name="ck_buyers_on_time_rate",
        ),
    )
    op.create_index("idx_buyers_merchant", "buyers", ["merchant_id"])
    op.create_table(
        "invoices",
        sa.Column("invoice_id", sa.String(25), primary_key=True),
        sa.Column("merchant_id", sa.String(20), sa.ForeignKey("merchants.merchant_id"), nullable=False),
        sa.Column("buyer_id", sa.String(30), sa.ForeignKey("buyers.buyer_id"), nullable=False),
        sa.Column("invoice_number", sa.String(50), nullable=False, unique=True),
        sa.Column("issue_date", sa.Date(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("payment_terms_days", sa.Integer(), nullable=False),
        sa.Column("subtotal_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("gst_rate", sa.Integer(), nullable=False),
        sa.Column("gst_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("total_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="INR"),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("amount_paid", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("paid_date", sa.Date(), nullable=True),
        sa.Column("days_overdue", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("risk_tier", sa.String(10), nullable=False),
        sa.Column("payment_link_id", sa.String(40), nullable=True),
        sa.Column("state", sa.String(20), nullable=False, server_default="created"),
        sa.Column("opted_out", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("edge_case", sa.String(30), nullable=False, server_default="none"),
        sa.Column("would_have_paid_without_intervention", sa.Boolean(), nullable=True),
        sa.Column("promise_outcome", sa.String(10), nullable=False, server_default="none"),
        sa.Column("split", sa.String(10), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("payment_terms_days IN (15, 30, 45, 60)", name="ck_invoices_terms"),
        sa.CheckConstraint("subtotal_amount > 0", name="ck_invoices_subtotal"),
        sa.CheckConstraint("gst_rate IN (0, 5, 12, 18, 28)", name="ck_invoices_gst_rate"),
        sa.CheckConstraint(
            "status IN ('paid', 'partial', 'pending', 'overdue', 'disputed')",
            name="ck_invoices_status",
        ),
        sa.CheckConstraint("days_overdue >= 0", name="ck_invoices_days_overdue"),
        sa.CheckConstraint("risk_tier IN ('low', 'medium', 'high')", name="ck_invoices_risk"),
        sa.CheckConstraint("split IN ('train', 'test')", name="ck_invoices_split"),
        sa.CheckConstraint(
            "promise_outcome IN ('none', 'pending', 'kept', 'broken')",
            name="ck_invoices_promise_outcome",
        ),
    )
    op.create_index("idx_invoices_merchant", "invoices", ["merchant_id"])
    op.create_index("idx_invoices_buyer", "invoices", ["buyer_id"])
    op.create_index("idx_invoices_status", "invoices", ["status"])
    op.create_index("idx_invoices_state", "invoices", ["state"])
    op.create_table(
        "interactions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("invoice_id", sa.String(25), sa.ForeignKey("invoices.invoice_id"), nullable=False),
        sa.Column("buyer_id", sa.String(30), nullable=False),
        sa.Column("channel", sa.String(10), nullable=False),
        sa.Column("direction", sa.String(10), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("message_text", sa.Text(), nullable=False),
        sa.Column("intent_label", sa.String(20), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("delivery_status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("attempt_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("channel IN ('whatsapp', 'email')", name="ck_interactions_channel"),
        sa.CheckConstraint("direction IN ('outbound', 'inbound')", name="ck_interactions_direction"),
        sa.CheckConstraint(
            "confidence IS NULL OR (confidence >= 0.0 AND confidence <= 1.0)",
            name="ck_interactions_confidence",
        ),
        sa.CheckConstraint(
            "delivery_status IN ('pending', 'sent', 'delivered', 'failed')",
            name="ck_interactions_delivery",
        ),
    )
    op.create_index("idx_interactions_invoice", "interactions", ["invoice_id"])
    op.create_index("idx_interactions_buyer", "interactions", ["buyer_id"])
    op.create_index("idx_interactions_idempotency", "interactions", ["invoice_id", "attempt_number"])
    op.create_table(
        "promises",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("invoice_id", sa.String(25), sa.ForeignKey("invoices.invoice_id"), nullable=False),
        sa.Column("source_interaction_id", sa.Uuid(), sa.ForeignKey("interactions.id"), nullable=False),
        sa.Column("promised_date", sa.Date(), nullable=False),
        sa.Column("promised_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("status", sa.String(10), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("confidence >= 0.7", name="ck_promises_confidence"),
        sa.CheckConstraint("status IN ('pending', 'kept', 'broken')", name="ck_promises_status"),
    )
    op.create_index("idx_promises_invoice", "promises", ["invoice_id"])
    op.create_table(
        "audit_log",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("invoice_id", sa.String(25), sa.ForeignKey("invoices.invoice_id"), nullable=False),
        sa.Column("from_state", sa.String(20), nullable=False),
        sa.Column("to_state", sa.String(20), nullable=False),
        sa.Column("actor", sa.String(20), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("reasoning_summary", sa.Text(), nullable=False),
        sa.Column("prev_hash", sa.String(64), nullable=False, server_default="0" * 64),
        sa.Column("row_hash", sa.String(64), nullable=False, server_default="0" * 64),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.CheckConstraint("actor IN ('agent', 'human', 'system')", name="ck_audit_actor"),
    )
    op.create_index("idx_audit_invoice", "audit_log", ["invoice_id"])
    op.create_table(
        "baseline_comparison",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("strategy", sa.String(30), nullable=False),
        sa.Column("eval_set_size", sa.Integer(), nullable=False),
        sa.Column("recovered_count", sa.Integer(), nullable=False),
        sa.Column("recovered_value", sa.Numeric(12, 2), nullable=False),
        sa.Column("total_value", sa.Numeric(12, 2), nullable=False),
        sa.Column("avg_days_to_recovery", sa.Float(), nullable=False),
        sa.Column("recovery_30d", sa.Float(), nullable=False),
        sa.Column("recovery_60d", sa.Float(), nullable=False),
        sa.Column("recovery_90d", sa.Float(), nullable=False),
        sa.Column("total_contacts_sent", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "strategy IN ('no_agent', 'naive_cadence', 'duebot')",
            name="ck_baseline_strategy",
        ),
    )
    op.create_index("idx_baseline_run", "baseline_comparison", ["run_id"])


def downgrade() -> None:
    """Drop all DueBot tables."""
    op.drop_table("baseline_comparison")
    op.drop_table("audit_log")
    op.drop_table("promises")
    op.drop_table("interactions")
    op.drop_table("invoices")
    op.drop_table("buyers")
    op.drop_table("merchants")
