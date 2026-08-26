import asyncio
from backend.db import create_engine, session_factory
from backend.config import get_settings
from backend.data.seed import seed_from_generator
from backend.models.audit_log import AuditLog
from backend.models.invoice import Invoice
from sqlalchemy import select

async def main():
    settings = get_settings()
    engine = create_engine(settings)
    maker = session_factory(engine)
    async with maker() as session:
        await seed_from_generator(session, num_invoices=260, seed=42)
        await session.commit()
        
        # Count audit rows
        res = await session.execute(select(AuditLog))
        all_logs = list(res.scalars())
        
        with_conf = [l for l in all_logs if l.extra_metadata and "confidence" in l.extra_metadata]
        abstained = [l for l in all_logs if l.extra_metadata and l.extra_metadata.get("abstained")]
        human_actors = [l for l in all_logs if l.actor == "human"]
        
        # Count invoices in human_review
        res_inv = await session.execute(select(Invoice).where(Invoice.state == "human_review"))
        hr_invoices = list(res_inv.scalars())
        
        print(f"Total audit logs: {len(all_logs)}")
        print(f"Logs with confidence: {len(with_conf)}")
        print(f"Logs with abstained: {len(abstained)}")
        print(f"Logs with actor='human': {len(human_actors)}")
        print(f"Invoices in human_review: {len(hr_invoices)}")
        
        for inv in hr_invoices:
            inv_logs = [l for l in all_logs if l.invoice_id == inv.invoice_id]
            print(f"\nInvoice {inv.invoice_id} in state {inv.state}:")
            for l in inv_logs:
                print(f"  [{l.actor}] {l.from_state} -> {l.to_state} | evt={l.extra_metadata.get('event') if l.extra_metadata else None} | conf={l.extra_metadata.get('confidence') if l.extra_metadata else None}")

asyncio.run(main())
