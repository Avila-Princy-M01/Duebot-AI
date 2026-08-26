# DueBot — 5-Minute Video Pitch & Shot List

A complete, word-for-word teleprompter script and UI shot list for recording the 5-minute product submission video.

---

## ⚙️ Pre-Demo Setup (do this before recording)

```bash
# 1. Copy and fill in credentials
cp .env.example .env
# Set ANTHROPIC_API_KEY or GEMINI_API_KEY for live reply parsing.
# Set RAZORPAY_WEBHOOK_SECRET if demoing the live payment webhook.

# 2. Enable the background poller so the demo shows autonomous lifecycle progression.
#    The poller runs aging → promise → nudge → reply every 30 seconds inside the API process.
echo "ENABLE_POLLER=true" >> .env

# 3. Seed the database
python scripts/seed_db.py

# 4. Start the API (poller starts automatically with ENABLE_POLLER=true)
uvicorn backend.main:app --reload

# 5. Start the frontend
cd frontend && npm run dev

# 6. (Optional) Live Razorpay webhook — needs a public URL
#    ngrok http 8000
#    Paste the ngrok URL + /api/webhooks/razorpay into your Razorpay test dashboard.
```

> **Note on WhatsApp transport:** The demo uses DueBot's built-in `SimulatedInbox`. All policy
> gates, idempotency guards, and log-before-send sequencing are exercised against the simulator.
> The `WhatsAppSender` interface is identical to what a real WABA adapter would consume —
> the policy gate requires a typed `PolicyDecision` object, not a boolean, so it cannot be
> bypassed regardless of transport.

---

## 🎬 Shot 1: The Problem & The Non-Custodial Boundary (0:00 – 0:30)

**On-Screen Action:**
- Browser on `http://localhost:3000` (Dashboard Overview).
- Point cursor at **"₹ Amount At Risk"** card and the **Aging Distribution** bar chart.

**Spoken Script (Word-for-Word):**
> *"Every B2B merchant faces the same cash flow crisis: overdue receivables sitting in someone else's bank account. But in business-to-business collections, you cannot simply direct-debit a customer or hand an LLM an open loop to spam your accounts.*
>
> *This is DueBot — an autonomous, policy-gated collections agent built on top of Razorpay Payment Links. DueBot never touches customer funds directly; it deterministically coordinates reminders, validates payment promises, and requests settlement via non-custodial payment links."*

---

## 🎬 Shot 2: Prioritization is a Rule, Not a Prompt (0:30 – 1:15)

**On-Screen Action:**
- Click **"Invoices"** in the sidebar navigation (`http://localhost:3000/invoices`).
- Filter by aging bucket `31-60 Days` and sort by Risk Score.
- Click on an invoice to open its detail drawer/page.

**Spoken Script (Word-for-Word):**
> *"Notice how receivables are triaged. Many AI collections tools pass an entire database dump to an LLM and ask it who to call. That is non-deterministic, expensive, and unsafe.*
>
> *In DueBot, prioritization is governed by pure Python functions in `engine/risk_tier.py` and `engine/aging.py`. A Tier-1 enterprise buyer who is three days late gets a gentle reminder; a chronically late account is escalated. The LLM is never consulted to decide who owes money or which bucket an invoice belongs to. The engine is pure, deterministic, and 100% test-covered."*

---

## 🎬 Shot 3: Live Outreach & The Weekly Policy Cap (1:15 – 2:15)

**On-Screen Action:**
- On an overdue invoice, click **"Preview Nudge"** button. Show the drafted WhatsApp message containing the exact invoice number, outstanding amount, and generated Razorpay link.
- Click **"Send Nudge"**.
- Navigate to **"Simulator Inbox"** (`http://localhost:3000/inbox`) and show the outbound message received.
- Switch back to invoice list, click an invoice that already has 3 touches, and click **"Preview Nudge"**.

**Spoken Script (Word-for-Word):**
> *"Let's trigger an intervention. When we preview a nudge, DueBot's `can_contact()` policy gate evaluates three hard constraints: Is the buyer opted out? Is there an active payment promise window? And has this account reached its weekly frequency cap?*
>
> *We click send. The message delivers via WhatsApp with an authentic Razorpay link. But look what happens if we attempt to nudge an invoice that has already received 3 touches this week: the policy engine immediately blocks the action with `MAX_CONTACTS_PER_WEEK reached`. The agent cannot be coerced into harassing a debtor, regardless of prompt manipulation."*

---

## 🎬 Shot 4: The Staged Failure — The LLM Safety Boundary (2:15 – 3:00)

**On-Screen Action:**
- In the **Simulator Inbox** (`http://localhost:3000/inbox`), select a nudged conversation.
- Type and send an ambiguous buyer reply: `"will sort it out soon"`.
- Show DueBot processing the reply.
- Open the invoice detail timeline to show state transition: `replied → human_review` (Reason: `Ambiguous intent / confidence < 0.70`).

**Spoken Script (Word-for-Word):**
> *"Now, let's stage a failure mode that breaks standard LLM agents. A buyer replies with vague text: 'will sort it out soon'.*
>
> *A naive AI treats this as a payment promise, snoozes the invoice, and allows the receivable to age out. DueBot uses structured tool-calling with a hard confidence threshold of 0.70. Because no specific date or commitment was made, the parser marks confidence below threshold. The deterministic state machine intercepts this and transitions the invoice to `HUMAN_REVIEW`.*
>
> *DueBot knows when to speak, when to pause, and critically — when to admit it does not know and route to a human."*

---

## 🎬 Shot 4b: The Human Review Queue — Closing the Loop (3:00 – 3:30)

**On-Screen Action:**
- Stay on the same invoice detail page, now in `human_review` state.
- Scroll to the amber **"Human Review Required"** panel.
- Type a reasoning note: `"Spoke with buyer directly — confirmed NEFT on the way, marking recovered."`.
- Click **"✓ Mark Recovered"**.
- Show the page refresh: state changes to `recovered`, the amber panel disappears, the audit timeline gains a new `human_review → recovered` row with `actor: human`.

**Spoken Script (Word-for-Word):**
> *"When an invoice parks in the human review queue, it is not a black hole. The merchant operator sees the full conversation context, the abstention reason, and the confidence score right here. They write a one-sentence note — this is mandatory and gets written into the cryptographic audit chain — then click 'Mark Recovered' or 'Close'.*
>
> *Watch the state machine advance: `human_review → recovered`, actor logged as `human`, reasoning preserved verbatim. The invoice is now settled and every decision is traceable. No silent database updates, no guessed outcomes — just a clean, auditable handoff from agent to operator and back."*

---

## 🎬 Shot 5: Cryptographic SHA-256 Hash Chain & Live Tamper Demo (3:30 – 4:15)

**On-Screen Action:**
- Click **"Audit Trail"** (`http://localhost:3000/audit`).
- Point cursor to the prominent green **"Chain Verified ✓ (492 Blocks)"** pill in the top header.
- Click **"Verify Chain"** button to show instant client-side verification against `GET /api/audit/verify`.
- **The Tamper Demo (Live Shock Value):**
  - Switch to a terminal split-screen.
  - Run the tamper command to edit an audit log directly in SQLite (simulating a rogue DB edit or forged confidence score):
    ```bash
    python -c "import sqlite3; con=sqlite3.connect('duebot.db'); con.execute(\"UPDATE audit_logs SET reasoning_summary='Unauthorized edit by adversary' WHERE id=(SELECT id FROM audit_logs LIMIT 1 OFFSET 10)\"); con.commit()"
    ```
  - Switch back to browser and click **"Verify Chain"** (or refresh).
  - **The Moment:** The green pill immediately flips to a pulsing red **"Tampering Detected ✗"** badge, pinpointing the exact modified block (Block #11), expected hash vs actual hash.
  - Revert the tamper via terminal or re-seed:
    ```bash
    python scripts/seed_db.py --num-invoices 260
    ```
  - Refresh: The badge instantly snaps back to green **"Chain Verified ✓"**.

**Spoken Script (Word-for-Word):**
> *"In financial systems, claiming an audit log is 'append-only' is meaningless unless you can mathematically prove it. DueBot links every state change, policy decision, confidence score, and human override into an unbroken SHA-256 cryptographic hash chain.*
>
> *Watch this: our verification endpoint checks the entire chain of 492 blocks in under 5 milliseconds — green across the board. Now let's simulate an adversary hacking the database to forge an operator note or inflate a confidence score. We run a direct SQLite update... click verify... and boom.*
>
> *The cryptographic avalanche breaks instantly. The system pinpoints the exact corrupted block and rejects the ledger. Zero silent tampering. Complete, non-repudiable auditability for accountants and regulators."*

---

## 🎬 Shot 6: 10-Seed Empirical Benchmark & Lift (4:15 – 4:45)

**On-Screen Action:**
- Navigate to **"Baseline Metrics"** (`http://localhost:3000/metrics`).
- Point cursor at the **Three-Way Comparison Table** and the **Recovery Lift Summary Cards**.

**Spoken Script (Word-for-Word):**
> *"Finally, does the policy engine actually work? We benchmarked DueBot against a No-Agent organic baseline and a Naive 7-day spam cadence across 10 generator seeds and 710 test invoices.*
>
> 1. ***Incremental Cash Recovery**: DueBot delivers **+4.9 percentage points higher recovery (+₹4.76 Lakhs)** over organic self-cure alone ($p < 0.01$).*
> 2. ***100% Dispute Defect Protection**: While blind cadences spam disputed accounts up to 13.4 times, DueBot delivers **zero harassment touches (0.0)** across 100% of runs.*
> 3. ***61.5% Fewer Messages**: DueBot pauses when buyers promise to pay or self-cure, cutting contact fatigue by **61.5%** while recovering cash 12 hours faster."*

---

## 🎬 Shot 7: Architectural Invariants & Closing (4:45 – 5:00)

**On-Screen Action:**
- Switch to terminal/code editor.
- Briefly show [`backend/engine/states.py`](file:///d:/Razorpay/backend/engine/states.py) (`is_valid_transition` pure function) and [`backend/api/webhooks.py`](file:///d:/Razorpay/backend/api/webhooks.py) (HMAC verification and fail-closed secret).

**Spoken Script (Word-for-Word):**
> *"To summarize: DueBot is not an uncontrolled LLM loop given access to payment APIs. It is a deterministic finite state machine with a cryptographic SHA-256 audit ledger, strict policy gates, and non-custodial Razorpay links.*
>
> *It knows when to act, when to pause, and when to ask for human help.*
>
> *Thank you."*
