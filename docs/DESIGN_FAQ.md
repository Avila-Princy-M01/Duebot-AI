# System Design & Architecture FAQ

1. **Isn’t this Razorpay Active Revenue Recovery?**
   Active Revenue Recovery retries failed recurring *debits*. DueBot automates unpaid B2B *invoices* (receivables), extracts payment promise dates over conversational channels, and escalates when promises break.

2. **How is the baseline comparison evaluated fairly?**
   All 3 evaluation strategies (`no_agent`, `naive_cadence`, `duebot`) share **one neutral, identical buyer response model** (`shared_should_settle` in `baselines.py`), evaluated with **paired within-seed statistics** and a **contact budget sweep** across 10 independent random generator seeds (~710 held-out test invoices):
   * **Incremental Recovery Lift (+4.93% ± 3.93%, +₹ 4.76L vs No-Agent)**: DueBot captures $+4.93\%$ higher recovery ($t = +3.96, p_t = 0.0033$, exact sign test $p = 0.0039$) than organic self-cure by actively recovering receivables from responsive debtors.
   * **100% Dispute Defect Protection Across All Budgets**: Naive cadence blindly spams disputed invoices (5.3 to 13.4 touches), whereas DueBot routes them to `HUMAN_REVIEW` with **0.0 touches**.
   * **46.4% to 61.5% Fewer Messages Across All Budgets**: Even at matched budget (`MAX_NAIVE = 3`), DueBot sends **46.4% fewer messages** (21.5 vs 40.1 touches) by selectively halting on self-cures and promises, rising to 61.5% fewer under default cadence.
   * **Recovery Rate Parity vs Naive (+0.77% ± 1.15%, 95% CI: [-0.05%, +1.60%])**: **5 wins, 0 losses, 5 ties** ($t = +2.12, p_t = 0.0626$, exact sign test $p = 0.0625$). DueBot is never worse than a blind loop on any seed, matching or exceeding recovery while eliminating spam.
   * **Faster and Quieter (-0.50 ± 0.10 days, p < 0.001)**: Across identical portfolios, DueBot's 3-day adaptive interval consistently accelerates resolution by 12 hours ($95\%\text{ CI}: [-0.57\text{d}, -0.43\text{d}]$, $t = -15.71, p < 0.001$, exact sign test $p = 0.0020$) while sending fewer total touches.

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
