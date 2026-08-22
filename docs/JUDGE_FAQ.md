# Judge FAQ (short answers)

1. **Isn’t this Razorpay Active Revenue Recovery?** That recovers failed *debits*. DueBot chases unpaid *invoices* (receivables) and tracks promises over time.
2. **Why not fine-tune?** No labeled corpus yet; tool-use + a locked template is auditable and what an MVP would ship.
3. **Hallucinated promise?** Promise logging requires `confidence >= 0.7` and a date. Below that → `HUMAN_REVIEW`.
4. **Why deterministic retries?** Money-adjacent policy must be predictable. The LLM does language, not cadence.
5. **Synthetic data too clean?** Generator injects ambiguous replies, opt-outs, duplicates, partials, paid-mid-sequence, promise-then-silent, disputes.
6. **False-positive cost?** A wasted human review on an invoice that would have self-cured — attention, not an auto-debit.
7. **Scale?** Per-invoice poll; LLM is only on inbound replies.
8. **Why WhatsApp first?** India collections reality; email is fallback.
9. **Most important metric?** ₹ recovered vs naive fixed-cadence on the same held-out batch.
10. **Dispute?** `intent=dispute` → never nudged again → human review.
11. **Just a CRM?** A CRM logs that you sent. DueBot logs what the buyer *committed* and whether they kept it.
12. **Crash mid-send?** Outbound rows are keyed `(invoice_id, attempt_number)`; log-before-send; pending rows are not retried as duplicates.
13. **Why not auto-debit?** B2B buyers don’t have standing mandates with every vendor. Payment Links only.
14. **If hired next?** Feed promise-kept history back into risk tier; merchant-editable policy.
15. **Vs generic dunning SaaS?** WhatsApp-first, GST invoices, Razorpay Payment Links, promise extraction with abstention.
16. **Threshold 0.7?** Named constant; below it we abstain. Tune on the train split, report on test.
17. **Why Postgres not a vector DB?** Structured state, not retrieval.
18. **Weakest part?** Code-mixed ambiguous replies — mitigated by abstention, not by guessing.
19. **Monetization?** Faster collections → working capital; natural next to Capital.
20. **Live failure case?** Hand-picked `will sort it out soon` is in the generator and the demo path.
