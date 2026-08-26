from datetime import date, datetime, timezone
from backend.data.generator import DueBotDataGenerator

SIM_TODAY = date(2026, 8, 21)
SIM_NOW = datetime(2026, 8, 21, 18, 0, 0, tzinfo=timezone.utc)

gen = DueBotDataGenerator(seed=42)
gen.run(num_invoices=260)
inbound_msgs = [m for m in gen.messages if m.direction == "inbound"]
print(f"Total inbound: {len(inbound_msgs)}")

for idx, m in enumerate(inbound_msgs):
    inv = next(i for i in gen.invoices if i.invoice_id == m.invoice_id)
    due_obj = date.fromisoformat(inv.due_date)
    msg_dt = datetime.fromisoformat(m.timestamp)
    if msg_dt.tzinfo is None:
        msg_dt = msg_dt.replace(tzinfo=timezone.utc)
    
    future_due = due_obj > SIM_TODAY
    future_msg = msg_dt > SIM_NOW
    print(f"[{idx}] {m.invoice_id}: intent={m.intent_label}, due={inv.due_date} (future={future_due}), msg_ts={m.timestamp} (future_msg={future_msg}), status={inv.status}")
