"""Three-way eval run ORM model."""

from __future__ import annotations

import datetime as dt
import uuid
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, Float, Index, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.db import Base


class BaselineComparison(Base):
    """One strategy's metrics inside a three-way eval run."""

    __tablename__ = "baseline_comparison"
    __table_args__ = (
        CheckConstraint(
            "strategy IN ('no_agent', 'naive_cadence', 'duebot')",
            name="ck_baseline_strategy",
        ),
        Index("idx_baseline_run", "run_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    strategy: Mapped[str] = mapped_column(String(30), nullable=False)
    eval_set_size: Mapped[int] = mapped_column(Integer, nullable=False)
    recovered_count: Mapped[int] = mapped_column(Integer, nullable=False)
    recovered_value: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    total_value: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    avg_days_to_recovery: Mapped[float] = mapped_column(Float, nullable=False)
    recovery_30d: Mapped[float] = mapped_column(Float, nullable=False)
    recovery_60d: Mapped[float] = mapped_column(Float, nullable=False)
    recovery_90d: Mapped[float] = mapped_column(Float, nullable=False)
    total_contacts_sent: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
