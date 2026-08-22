# Offline Fallback Benchmark (`docs/FALLBACK_CLASSIFIER_EVAL.md`)

Evaluates intent classification performance on 50 held-out B2B buyer reply test cases.

---

## Executive Summary

* **Engine**: `Offline Keyword Fallback Classifier` (50 fallbacks).
* **Dataset**: 50 held-out B2B test cases (unseen during dev).
* **Accuracy**: **44.0%** (22/50).
* **High-Confidence Precision (`>= 0.7`)**: **92.3%**.
* **Abstention Rate (`< 0.7`)**: **74.0%** (37 cases routed to `HUMAN_REVIEW`).

---

## Per-Class Precision, Recall & F1-Score

| Intent Class | Precision | Recall | F1 Score | Support |
|--------------|-----------|--------|----------|---------|
| `promise` | 80.0% | 33.3% | 47.1% | 12 |
| `ambiguous` | 27.0% | 100.0% | 42.5% | 10 |
| `dispute` | 100.0% | 40.0% | 57.1% | 10 |
| `opt_out` | 100.0% | 37.5% | 54.5% | 8 |
| `objection` | 100.0% | 10.0% | 18.2% | 10 |

---

## Confusion Matrix

| Expected \ Predicted | promise | dispute | opt_out | objection | ambiguous |
|----------------------|---------|---------|---------|-----------|-----------|
| **promise** | 4 | 0 | 0 | 0 | 8 |
| **dispute** | 0 | 4 | 0 | 0 | 6 |
| **opt_out** | 0 | 0 | 3 | 0 | 5 |
| **objection** | 1 | 0 | 0 | 1 | 8 |
| **ambiguous** | 0 | 0 | 0 | 0 | 10 |

---

## Fallback Classifier Analysis

1. **Purpose**: Used exclusively when LLM API keys are unconfigured or during API outages.
2. **Held-Out Performance**: Evaluates simple regex/token matching rules on held-out data.
3. **Safety Guarantee**: High-confidence keyword matches trigger safe policy actions;
   uncertain texts fallback to `AMBIGUOUS` (confidence 0.20) for human review.

