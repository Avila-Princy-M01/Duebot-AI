from backend.data.generator import DueBotDataGenerator

gen = DueBotDataGenerator(seed=42)
gen.run(num_invoices=260)
inbound_msgs = [m for m in gen.messages if m.direction == "inbound"]
print(f"Total inbound messages in gen: {len(inbound_msgs)}")

intent_counts = {}
for m in inbound_msgs:
    intent_counts[m.intent_label] = intent_counts.get(m.intent_label, 0) + 1
print("Inbound intent counts:", intent_counts)

# Let's inspect why they were skipped in seed.py
inbound_inv_ids = {m.invoice_id for m in inbound_msgs}
matching_invs = [i for i in gen.invoices if i.invoice_id in inbound_inv_ids]
print(f"Matching invoices in gen: {len(matching_invs)}")

for idx, i in enumerate(matching_invs):
    msg = next(m for m in inbound_msgs if m.invoice_id == i.invoice_id)
    outbound = [m for m in gen.messages if m.invoice_id == i.invoice_id and m.direction == "outbound"]
    print(f"[{idx}] Inv {i.invoice_id}: status={i.status}, edge={i.edge_case}, outcome={i.promise_outcome}, msg_intent={msg.intent_label}, due={i.due_date}, paid={i.paid_date}, num_outbound={len(outbound)}")
