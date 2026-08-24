"""Assistant schemas for interactive natural language & voice querying."""

from __future__ import annotations

from pydantic import BaseModel


class AssistantQueryRequest(BaseModel):
    """Query payload from merchant/UI."""

    query: str
    buyer_id: str | None = None
    invoice_id: str | None = None


class AssistantQueryResponse(BaseModel):
    """Structured response from DueBot assistant."""

    answer: str
    spoken_answer: str
    category: str
    suggested_action: str | None = None
    model: str
