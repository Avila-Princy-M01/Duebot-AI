# Evaluation methodology

The eval harness is **not** a unit test. It proves product lift on the **same held-out invoices** the synthetic generator marks `split=test` (≈30% of a seeded batch). It never uses placeholder rows.

## Conditions

1. **no_agent** — only invoices labeled `would_have_paid_without_intervention` recover. Zero contacts.
2. **naive_cadence** — a reminder every 7 days up to a naive cap; recovers self-cure plus some extra late payers. No promise extraction, no abstention.
3. **duebot** — contact cap 3, disputes go to human review with zero nudges, promises kept/broken drive recovered vs escalated.

All three consume `backend.data.generator.DueBotDataGenerator` output. Metrics are computed by `backend.engine.recovery_metrics.recovery_report`.

## Metrics

| Metric | Definition |
|--------|------------|
| Recovery rate | Recovered invoice value / batch value |
| 30/60/90d | Recovered if `paid_date - due_date` is within the horizon |
| Promise-kept rate | kept / (kept + broken) |
| False-escalation rate | Among escalated/human_review, share with `would_have_paid_without_intervention=True` |
| Contacts | Outbound count attributed to the strategy |

## How to run

```bash
python scripts/run_eval.py
```

Writes `tests/eval/last_report.json`. `GET /api/metrics/baseline` persists a three-way `baseline_comparison` run if the table is empty.
