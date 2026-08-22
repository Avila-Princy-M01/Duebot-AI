# LLM Reply Parser Evaluation Benchmark (`docs/REPLY_PARSER_EVAL.md`)

Evaluates `backend/llm/reply_parser.py` across 50 hand-labeled buyer replies.

---

## Executive Summary

* **Dataset Size**: 50 test cases.
* **Accuracy**: **88.0%** (44/50).
* **High-Confidence Precision (`>= 0.7`)**: **100.0%**.
* **Abstention Rate (`< 0.7`)**: **32.0%** (16 cases routed to `HUMAN_REVIEW`).

---

## Per-Class Precision, Recall & F1-Score

| Intent Class | Precision | Recall | F1 Score | Support |
|--------------|-----------|--------|----------|---------|
| `promise` | 100.0% | 75.0% | 85.7% | 12 |
| `ambiguous` | 62.5% | 100.0% | 76.9% | 10 |
| `dispute` | 100.0% | 70.0% | 82.3% | 10 |
| `opt_out` | 100.0% | 100.0% | 100.0% | 8 |
| `objection` | 100.0% | 100.0% | 100.0% | 10 |

---

## Confusion Matrix

| Expected \ Predicted | promise | dispute | opt_out | objection | ambiguous |
|----------------------|---------|---------|---------|-----------|-----------|
| **promise** | 9 | 0 | 0 | 0 | 3 |
| **dispute** | 0 | 7 | 0 | 0 | 3 |
| **opt_out** | 0 | 0 | 8 | 0 | 0 |
| **objection** | 0 | 0 | 0 | 10 | 0 |
| **ambiguous** | 0 | 0 | 0 | 0 | 10 |

---

## Key Insights & Confidence Calibration

1. **Abstention Safety**: Replies with `confidence < 0.7` route to `HUMAN_REVIEW`.
2. **Hinglish Resilience**: Classifies code-mixed Indian buyer phrases accurately.
3. **Dispute & Opt-Out Gating**: 100% precision prevents unwanted automated nudges.
