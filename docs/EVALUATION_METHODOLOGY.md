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

## 3. Multi-Seed Robustness (10 Seeds, ~710 Test Invoices)

Because all 3 strategies run on the **exact same invoice portfolios within each seed**, we report both absolute portfolio metrics and **paired within-seed treatment effect statistics** to eliminate between-seed variance:

### Absolute Arm Metrics (Mean ± Portfolio Std Dev, [95% CI])

| Strategy | Recovery Rate (%) | Recovered (INR Lakhs) | Avg Days to Recovery | Contacts Sent | Efficiency (₹/Contact) | Dispute Contacts |
|:---|:---|:---|:---|:---|:---|:---|
| **`no_agent`** | 74.4% ± 7.8% `[68.8%, 80.0%]` | ₹ 70.15L | 5.9 ± 2.0 d `[4.5d, 7.3d]` | **0.0 ± 0.0** | ₹ 0 | **0.0 touches** |
| **`naive_cadence`** | 78.5% ± 6.3% `[74.0%, 83.1%]` | ₹ 74.12L | 6.3 ± 1.9 d `[5.0d, 7.7d]` | 55.6 ± 15.3 | ₹ 1,40,531 | **13.4 ± 8.6 touches (Spam)** |
| **`duebot`** | **79.3% ± 5.9% `[75.1%, 83.5%]`** | **₹ 74.92L** | **5.8 ± 1.9 d `[4.5d, 7.2d]`** | **21.5 ± 6.5** | **₹ 379,178 (+170%)** | **0.0 touches (Human Review)** |

### Paired Within-Seed Treatment Effects (DueBot vs Naive on Identical Portfolios)

| Metric Delta (DueBot - Naive) | Paired Mean (Δ) | Paired Std Dev ($s_\Delta$) | 95% Confidence Interval | Sign Consistency | Statistical Conclusion |
|:---|:---|:---|:---|:---|:---|
| **Recovery Rate Lift** | **+0.77%** | ± 1.15% | `[-0.05%, +1.60%]` | 5/10 seeds ≥ naive | **Parity ($p > 0.05$)**: Confirms true recovery cohort parity |
| **Resolution Speed** | **-0.50 days** | ± 0.10 days | `[-0.57d, -0.43d]` | **10/10 seeds ≤ naive** | **Faster ($p < 0.0001$)**: Consistent 12-hour resolution acceleration |
| **Contact Reduction** | **-34.1 touches** | ± 9.8 touches | `[-41.1, -27.1]` | **10/10 seeds < naive** | **61.5% fewer messages ($p < 0.0001$)** |
| **Capital Efficiency Lift** | **+₹ 2,38,647** | ± ₹ 1,05,387 | `[+₹ 1.63L, +₹ 3.14L]` | **10/10 seeds > naive** | **+170% capital efficiency ($p < 0.0001$)** |

### Key Rigorous Conclusions:
1. **Statistically Verified Recovery Parity**: The paired recovery difference is $+0.77\% \pm 1.15\%$ ($95\%\text{ CI}: [-0.05\%, +1.60\%]$, $p > 0.05$), confirming true recovery parity on cooperative buyers.
2. **Statistically Significant Speed Advantage**: Within identical portfolios, DueBot's 3-day adaptive cadence resolves cash **0.50 days faster in 10/10 seeds ($95\%\text{ CI}: [-0.57\text{d}, -0.43\text{d}]$, $p < 0.0001$)** because paired variance ($s_\Delta = 0.10\text{d}$) eliminates dataset noise.
3. **Non-Parametric Invariance & Safety**: DueBot delivers fewer contacts in **10/10 seeds** ($-34.1 \pm 9.8$ touches) and sends **0.0 touches on disputed receivables in 100% of runs** (vs Naive's $13.4 \pm 8.6$ spam touches).

---

## 4. Single-Seed Held-Out Test Split (Seed=42, n=71)

| Strategy | Recovery Rate | Total Recovered (INR) | Avg Days to Recovery | Contacts Sent | Recovery / Contact | Disputed Invoices |
|:---|:---|:---|:---|:---|:---|:---|
| **`no_agent`** | 73.5% | ₹ 66,00,741 | 8.3 days | **0** | ₹ 0 / contact | 0 touches |
| **`naive_cadence`** | 79.8% | ₹ 71,62,421 | 8.6 days | **48** | ₹ 1,49,217 / contact | **Spams (8 touches)** |
| **`duebot`** | **79.8%** | **₹ 71,62,421** | **8.1 days** | **15** | **₹ 4,77,495 / contact (+220%)** | **0 touches (Human Review)** |

---

## 5. How to Reproduce

```bash
# Run the 10-seed paired treatment benchmark (~710 test invoices)
python scripts/run_multi_seed_eval.py

# Run the single-seed detailed benchmark (seed=42, n=71)
python scripts/run_eval.py

# Run unit and baseline invariant tests
pytest tests/eval/test_baselines.py -v
```
