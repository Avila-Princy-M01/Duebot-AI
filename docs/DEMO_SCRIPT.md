# DueBot — 5-minute demo script

**0:00–0:30 — The number.** Open the overview. Point at ₹ at risk and the aging buckets. “This synthetic SME has overdue B2B invoices sitting in someone else’s bank. DueBot does not move that money — it only asks, via a Payment Link.”

**0:30–1:15 — Prioritization is a rule, not a prompt.** Open an invoice list. High-risk / high-aging vs a reliable buyer three days late. Risk tier and aging come from `engine/risk_tier.py` and `engine/aging.py`. Claude is not involved.

**1:15–2:15 — Two live interventions.** On an overdue invoice: Preview nudge (policy reason + drafted body with verbatim amount/invoice number). Send. Inbox shows the outbound WhatsApp (simulated). Then a second invoice: buyer will not reply — explain the weekly cap of 3.

**2:15–3:00 — The failure, staged.** On a nudged invoice paste: `will sort it out soon`. DueBot must **not** log a promise. Audit row: `replied → human_review`, reasoning about confidence / no date. This is `CONFIDENCE_THRESHOLD = 0.7` plus `event_for_parsed_intent`.

**3:00–4:00 — Audit + metrics.** Scroll the append-only log for one invoice. Then open the 3-Way Metrics evaluation: no-agent vs naive 7-day cadence vs DueBot on held-out generator splits (`python scripts/run_multi_seed_eval.py`). The headline is the efficiency + safety delta verified across 10 random seeds: DueBot recovers the full responsive cohort with 61.5% fewer contacts (46%–61% fewer across all contact budgets), 0 spam touches on disputed receivables (vs Naive sending 5.3 to 13.4 spam touches), and 0 false promises.

**4:00–4:30 — Close.** “This is a state machine that knows when to talk, what to say, when to stop, and when to admit it doesn’t know. The LLM only classified the sentence and phrased the template.”
