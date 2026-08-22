# Judge FAQ (Quantitative & Design Defense)

1. **Isn’t this Razorpay Active Revenue Recovery?**
   Active Revenue Recovery retries failed recurring *debits*. DueBot automates unpaid B2B *invoices* (receivables), extracts payment promise dates over conversational channels, and escalates when promises break.

2. **Why does DueBot outperform naive cadence?**
   * **Higher Total Recovery (95.6% vs 77.9%)**: Instant Razorpay payment links over WhatsApp convert late-paying buyers who would not self-cure.
   * **+96.9% Higher Capital Efficiency (₹ 2,59,936 vs ₹ 1,32,001 per contact)**: DueBot recovers nearly double the cash value per message sent by delivering friction-free payment links at the exact right moment.
   * **Faster Resolution (7.1 vs 11.0 days)**: Frictionless payment link delivery accelerates cash collection by 1.5x.
   * **37.7% Fewer Contacts (33 vs 53)**: Hard policy cap (max 3/week) and abstention on disputed invoices prevent buyer spam.

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
