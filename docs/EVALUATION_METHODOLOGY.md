# Evaluation Methodology & Benchmark Specification

The evaluation harness measures DueBot's autonomous collections performance against counterfactual baselines on a held-out test dataset (`split=test`, seed=42, $n=71$ invoices).

It does **not** run on static mocks or analytical approximations: **the eval directly executes DueBot's real deterministic engine, policy gates, scheduler, and state machine day-by-day across the simulated timeline.**

---

## 1. The Three Evaluation Arms

All three strategies are evaluated on the exact same held-out invoices and share **one neutral, identical ground-truth buyer response model** (`shared_should_settle` in `backend/data/baselines.py`):

1. **`no_agent` (Null Counterfactual)**:
   - Zero outbound contacts sent.
   - Invoices only settle if the buyer was going to self-cure organically (`would_have_paid_without_intervention=True`).

2. **`naive_cadence` (Fixed-Interval Loop Counterfactual)**:
   - A blind, static reminder every 7 days (`NAIVE_CADENCE_DAYS = 7`).
   - **Lacks a policy gate**: It has no `can_contact` check, no dispute detection, and no promise awareness.
   - Consequently, it sends unnecessary touches on disputed invoices and pesters buyers regardless of commitment dates.

3. **`duebot` (Autonomous Collections Agent)**:
   - Driven directly by the real engine: [`aging.py`](file:///d:/Razorpay/backend/engine/aging.py), [`scheduler.next_action_at`](file:///d:/Razorpay/backend/engine/scheduler.py), [`policy.can_contact`](file:///d:/Razorpay/backend/engine/policy.py), [`policy.event_for_parsed_intent`](file:///d:/Razorpay/backend/engine/policy.py), and [`states.transition`](file:///d:/Razorpay/backend/engine/states.py).
   - Enforces a hard weekly contact ceiling (`MAX_CONTACTS_PER_WEEK = 3`), respects promise grace periods, and immediately halts outreach on disputes (`HUMAN_REVIEW` with 0 contacts).

---

## 2. Neutral Buyer Settlement Model

To avoid "thumb-on-the-scale" bias, no arm receives custom conversion rules. The single function `shared_should_settle` governs whether a buyer pays on any given clock tick:
- **Organic Self-Cure**: Buyer settles 3 days post-due without outreach.
- **Kept Promise**: Buyer settles on their promised date after receiving a touch, provided outreach respected their commitment window.
- **Nudge Conversion**: Non-disputed, non-broken-promise buyer settles after receiving $\ge 2$ touches.
- **Disputed Invoices**: Automated reminders never force settlement on disputed receivables.

---

## 3. Measured Results & Honest Findings

| Strategy | Recovery Rate | Total Recovered (INR) | Avg Days to Recovery | Contacts Sent | Recovery / Contact | Disputed Invoices |
|:---|:---|:---|:---|:---|:---|:---|
| **`no_agent`** | 73.5% | ₹ 66,00,741 | 8.3 days | **0** | ₹ 0 / contact | 0 touches |
| **`naive_cadence`** | 79.8% | ₹ 71,62,421 | 8.6 days | **48** | ₹ 1,49,217 / contact | **Spams (8 touches)** |
| **`duebot`** | **79.8%** | **₹ 71,62,421** | **8.1 days** | **36** | **₹ 1,98,956 / contact (+33.3%)** | **0 touches (Human Review)** |

### Key Conclusions:
1. **Recovery Cohort Parity**: On this dataset, both DueBot and a blind 7-day loop reach the responsive recovery cohort (79.8% / ₹ 71.62L). We do **not** claim inflated recovery lift on cooperative buyers.
2. **+33.3% Capital Efficiency (25.0% Fewer Messages)**: DueBot recovers the exact same capital with **36 touches instead of 48**, saving merchant messaging costs and preserving customer goodwill.
3. **Emergent Speed Advantage (8.1 vs 8.6 Days)**: DueBot's 3-day adaptive interval enables responsive buyers to settle on Day 6 rather than waiting for Naive's Day 7 tick — with zero hardcoded date overrides.
4. **Dispute Defect Prevention**: Naive sends 8 spam contacts to buyers disputing their invoices. DueBot's policy gate halts outreach immediately, eliminating brand damage and compliance risk.

---

## 4. How to Reproduce

```bash
# Run the 3-way evaluation benchmark
python scripts/run_eval.py

# Run unit and invariant tests
pytest tests/eval/test_baselines.py -v
```
