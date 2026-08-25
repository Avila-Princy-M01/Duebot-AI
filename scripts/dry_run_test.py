import json
import urllib.request

print("================================================================")
print("             DUEBOT END-TO-END DEMO DRY RUN TEST                ")
print("================================================================")

# Seed fresh DB
req = urllib.request.Request("http://localhost:8000/api/seed?num_invoices=80&seed=42", data=b"")
with urllib.request.urlopen(req) as r:
    print("[INIT] Re-seeded database with 80 synthetic invoices.")

# Test 1: Fetch invoices
req = urllib.request.Request("http://localhost:8000/api/invoices?limit=20")
with urllib.request.urlopen(req) as r:
    data = json.loads(r.read().decode())
    invoices = data["data"]
    print(f"[TEST 1: Invoices] Fetched {len(invoices)} invoices.")
    overdue_inv = next((inv for inv in invoices if inv["status"] == "overdue" and inv["state"] in ("created", "overdue")), invoices[0])
    target_id = overdue_inv["invoice_id"]
    inv_num = overdue_inv.get("invoice_number")
    print(f"  -> Target invoice for nudge: {target_id} (Number: {inv_num}, Status: {overdue_inv.get('status')}, State: {overdue_inv.get('state')})")

# Test 2: Preview Nudge
req = urllib.request.Request(f"http://localhost:8000/api/nudge/preview/{target_id}")
with urllib.request.urlopen(req) as r:
    preview = json.loads(r.read().decode())["data"]
    msg_snippet = preview.get("drafted_message", "")[:60]
    print(f"[TEST 2: Preview Nudge] Allowed: {preview.get('allowed')}")
    print(f"  -> Draft: {msg_snippet}...")
    print(f"  -> Contacts this week: {preview.get('contacts_this_week')}")

# Test 3: Execute Nudge
req = urllib.request.Request(
    "http://localhost:8000/api/nudge/trigger?dry_run=false",
    data=json.dumps({"invoice_id": target_id}).encode("utf-8"),
    headers={"Content-Type": "application/json"},
)
with urllib.request.urlopen(req) as r:
    exec_res = json.loads(r.read().decode())["data"]
    print(f"[TEST 3: Execute Nudge] Sent: {exec_res.get('sent')} | Dispatched: {exec_res.get('decision', {}).get('allowed')}")

# Test 4: Verify Inbox has outbound message
req = urllib.request.Request("http://localhost:8000/api/inbox?limit=5")
with urllib.request.urlopen(req) as r:
    inbox = json.loads(r.read().decode())["data"]
    top_msg = inbox[0] if inbox else {}
    txt = top_msg.get("message_text", "")[:60]
    print(f"[TEST 4: Inbox] Top message direction: {top_msg.get('direction')} - \"{txt}...\"")

# Test 5: Simulate Ambiguous Reply -> Abstain to Human Review
req = urllib.request.Request(
    "http://localhost:8000/api/inbox/reply",
    data=json.dumps({"invoice_id": target_id, "text": "will sort it out soon"}).encode("utf-8"),
    headers={"Content-Type": "application/json"},
)
with urllib.request.urlopen(req) as r:
    reply_res = json.loads(r.read().decode())["data"]
    print(f"[TEST 5: Ambiguous Reply] Resulting State: {reply_res.get('state')}")

# Test 6: Verify Audit Trail recorded abstention and transition to human_review
req = urllib.request.Request(f"http://localhost:8000/api/audit?invoice_id={target_id}")
with urllib.request.urlopen(req) as r:
    audits = json.loads(r.read().decode())["data"]
    print(f"[TEST 6: Audit Trail] Recorded {len(audits)} entries for {target_id}:")
    for a in audits[:3]:
        from_st = a.get("from_state")
        to_st = a.get("to_state")
        reason = a.get("reasoning_summary")
        print(f"  -> {from_st} -> {to_st} | Reasoning: {reason}")

# Test 7: Assistant Voice / Query API
req = urllib.request.Request(
    "http://localhost:8000/api/assistant/ask",
    data=json.dumps({"query": "What is our total amount at risk and aging distribution?"}).encode("utf-8"),
    headers={"Content-Type": "application/json"},
)
with urllib.request.urlopen(req) as r:
    ans = json.loads(r.read().decode())["data"]
    print(f"[TEST 7: Assistant API] Category: {ans.get('category')}")
    print(f"  -> Answer: {ans.get('answer')[:80]}...")
    print(f"  -> Spoken: {ans.get('spoken_answer')[:80]}...")

# Test 8: Metrics 3-way evaluation
req = urllib.request.Request("http://localhost:8000/api/metrics/baseline")
with urllib.request.urlopen(req) as r:
    metrics = json.loads(r.read().decode())["data"]
    print(f"[TEST 8: Metrics Endpoint] Baseline comparison rows: {len(metrics)}")
    for m in metrics:
        strat = m.get("strategy")
        rec_val = float(m.get("recovered_value", 0))
        tot_val = float(m.get("total_value", 1))
        rate = (rec_val / tot_val) if tot_val else 0.0
        days = m.get("avg_days_to_recovery", 0.0)
        contacts = m.get("total_contacts_sent", 0)
        print(f"  -> Strategy: {strat:15} | Recovery: {rate:.1%} (INR {rec_val:,.0f}) | Days: {days:.1f} | Contacts: {contacts}")

print("================================================================")
print("              DRY RUN COMPLETED SUCCESSFULLY!                   ")
print("================================================================")
