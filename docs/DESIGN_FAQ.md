# System Design & Architecture FAQ

1. **Isn’t this Razorpay Active Revenue Recovery?**
   Active Revenue Recovery retries failed recurring *debits*. DueBot automates unpaid B2B *invoices* (receivables), extracts payment promise dates over conversational channels, and escalates when promises break.

2. **How is the baseline comparison evaluated fairly?**
   All 3 evaluation strategies (`no_agent`, `naive_cadence`, `duebot`) share **one neutral, identical buyer response model** (`shared_should_recover` in `baselines.py`). Recovery outcomes are driven strictly by ground-truth generator labels, not arm-specific rules:
   * **Equal Recovery Rate (79.8% / ₹ 71.62L)**: Both DueBot and naive cadence reach the nudge-responsive cohort. We do not claim an artificial recovery boost on cooperative buyers.
   * **+220% Higher Capital Efficiency (₹ 4,77,495 vs ₹ 1,49,217 per contact)**: DueBot achieves maximum recovery with **68.8% fewer contacts** (15 vs 48).
   * **Faster Resolution (8.1 vs 8.6 days)**: Emerges naturally from DueBot's 3-day adaptive interval vs Naive's static 7-day grid.
   * **Dispute Abstention**: Naive cadence blindly spams disputed invoices (8 contacts), whereas DueBot routes them to `HUMAN_REVIEW` with 0 contacts.

3. **What happens on disputed or ambiguous replies?**
   `intent=dispute` or low-confidence replies (`confidence < 0.7`) immediately halt automated nudging and route the invoice to `HUMAN_REVIEW` (0 contacts sent, 0% false escalations).

4. **Why not fine-tune or use a LangChain agent loop?**
   Money-adjacent actions must be auditable and safe. Hand-rolled state machine + tool-use guarantees zero non-deterministic loops.

5. **Hallucinated promise?**
   Promise logging requires `confidence >= 0.7` and an explicit target date. Below that → `HUMAN_REVIEW`.

6. **Why deterministic retries & scheduling?**
   Collections cadence must be predictable for auditability. The LLM handles natural language interpretation, while `engine/policy.py` controls timing.

7. **Is synthetic data realistic?**
   The generator injects 7 explicit edge cases: ambiguous replies, mid-sequence opt-outs, duplicate invoices, partial payments, paid-mid-sequence, promise-then-silent, and disputed invoices.

8. **False-positive cost?**
   A wasted human review on an invoice that would have self-cured — an attention cost, never an auto-debit or financial risk.

9. **Scale and throughput?**
   Per-invoice poll loop without heavy queue overhead; LLM tool-calling is invoked only when an inbound reply is received.

10. **Why WhatsApp-first?**
    WhatsApp is the primary business communication channel for Indian SMEs. Email is integrated as a secondary fallback.

11. **Just a CRM?**
    A CRM logs that you sent a message. DueBot extracts what the buyer *committed to*, tracks whether they kept the promise, and triggers state transitions automatically.

12. **Crash mid-send resilience?**
    Outbound interactions are keyed by `(invoice_id, attempt_number)` with log-before-send semantics to prevent duplicate nudges.

13. **Why not auto-debit?**
    B2B buyers do not grant standing auto-debit mandates to vendors. Razorpay Payment Links are the canonical, compliant payment mechanism.

14. **Why Postgres instead of a vector DB?**
    B2B collections require structured state, atomic transactions, and immutable audit logs — not vector retrieval.

15. **What is the weakest part of the system?**
    Code-mixed Hinglish ambiguous replies — mitigated by strict confidence threshold abstention (`confidence < 0.7` ➔ `HUMAN_REVIEW`) rather than guessing.
