"""API health + merchants happy path / 404."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health(client: AsyncClient) -> None:
    """Health returns the success envelope."""
    response = await client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["status"] == "ok"
    assert "request_id" in body["meta"]


@pytest.mark.asyncio
async def test_merchant_404(client: AsyncClient) -> None:
    """Missing merchant is a structured 404."""
    response = await client.get("/api/merchants/MER-999")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


@pytest.mark.asyncio
async def test_create_and_list_merchant(client: AsyncClient) -> None:
    """POST then GET merchants."""
    created = await client.post(
        "/api/merchants",
        json={
            "business_name": "Test Traders",
            "business_type": "wholesale",
            "gstin": "27AAAAA0000A1Z5",
            "city": "Pune",
            "state_code": "27",
        },
    )
    assert created.status_code == 200
    listed = await client.get("/api/merchants")
    assert listed.status_code == 200
    assert listed.json()["meta"]["total_count"] >= 1


@pytest.mark.asyncio
async def test_list_invoices_state_filter(client: AsyncClient) -> None:
    """GET /api/invoices?state=... filters specifically on the 11-state machine state."""
    res_all = await client.get("/api/invoices?limit=200")
    assert res_all.status_code == 200

    res_nudged = await client.get("/api/invoices?state=nudged")
    assert res_nudged.status_code == 200
    for inv in res_nudged.json()["data"]:
        assert inv["state"] == "nudged"

    res_overdue = await client.get("/api/invoices?state=overdue")
    assert res_overdue.status_code == 200
    for inv in res_overdue.json()["data"]:
        assert inv["state"] == "overdue"
