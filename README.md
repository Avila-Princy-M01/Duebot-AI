# DueBot

An AI collections agent for overdue **B2B receivables**, built for the Razorpay AI Buildathon 2026 (Track 03 — AI Revenue Recovery).

DueBot monitors a merchant's overdue invoices, decides **when** to nudge (WhatsApp-first, hard weekly contact caps), parses buyer replies into structured intents, tracks promise-to-pay dates, and escalates when a promise breaks or when model confidence is low. It **never moves money**. It only requests payment via Razorpay Payment Links. Every state transition is recorded in an append-only audit log.

**DueBot** couples a deterministic state machine and policy engine with an LLM periphery for promise extraction, backed by an empirical three-way baseline evaluation.

---

## Architecture

```mermaid
flowchart LR
  UI[Next.js Dashboard]
  API[FastAPI Backend]
  ENG[Deterministic Engine: Aging Policy States]
  LLM[LLM: Reply Parser Drafter]
  DB[(PostgreSQL / SQLite)]
  RZP[Razorpay Webhook / API]

  UI --> API
  API --> ENG
  API --> DB
  API --> LLM
  RZP -->|Payment Link Webhook| API
  LLM -->|"Structured Intent + Confidence"| ENG
```

The LLM never decides whether to act. Pure deterministic functions in `backend/engine/policy.py` and `backend/engine/states.py` govern all transitions and actions.

Full design: [ARCHITECTURE.md](ARCHITECTURE.md) · Architecture FAQ: [docs/DESIGN_FAQ.md](docs/DESIGN_FAQ.md) · Evaluation Methodology: [docs/EVALUATION_METHODOLOGY.md](docs/EVALUATION_METHODOLOGY.md) · Demo Walkthrough: [docs/DEMO_SCRIPT.md](docs/DEMO_SCRIPT.md).

---

## Quickstart

```bash
# 1. Install dependencies
python -m pip install -e ".[dev]"
copy .env.example .env

# 2. Start backend server (SQLite local mode)
uvicorn backend.main:app --reload --port 8000

# 3. Seed demo dataset (in a separate terminal)
python scripts/seed_db.py --num-invoices 80

# 4. Start frontend dashboard
cd frontend && npm install && npm run dev
```

Generate synthetic datasets independently:

```bash
python -m backend.data.generator --num-invoices 260 --seed 42
```

---

## API Summary

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/health` | Service health & liveness |
| GET/POST | `/api/merchants` | Merchant profile management |
| GET | `/api/invoices` | Filterable invoice list with risk & aging |
| GET | `/api/invoices/{id}` | Invoice detail with audit history |
| POST | `/api/invoices/ingest` | Multipart CSV receivable ingestion |
| GET | `/api/buyers` | Buyer directory & risk profiles |
| POST | `/api/nudge/trigger?dry_run=` | Policy evaluation → draft → dispatch |
| GET | `/api/nudge/preview/{id}` | Read-only policy & draft preview |
| GET | `/api/promises` | Promise-to-pay commitment tracker |
| GET | `/api/audit` | Append-only state transition audit log |
| GET | `/api/metrics/recovery` | Live database recovery metrics |
| GET | `/api/metrics/baseline` | Three-way baseline evaluation metrics |
| POST | `/api/webhooks/razorpay` | Razorpay payment link status webhook |
| POST | `/api/inbox/reply` | Simulated buyer WhatsApp inbound reply |
| POST | `/api/seed` | Reset & seed database from generator |

All responses return standard envelopes: `{"data": ..., "meta": {"timestamp", "request_id", "total_count"}}`.

---

## Simulation Boundary (What is Real vs. What is Modeled)

We make the system boundaries explicit and transparent:

| Component | Status | Details |
|:---|:---|:---|
| **Core Collections Engine** | **100% Real** | Deterministic state machine (`states.py`), policy guard (`can_contact`), scheduler (`scheduler.py`), aging engine (`aging.py`). Pure functions, zero mocks. |
| **LLM Periphery** | **100% Real** | Structured tool-use intent parsing (`ReplyParser`) and deterministic fallback classifier (`fallback_intent`). |
| **API & Database** | **100% Real** | FastAPI backend, SQLite/PostgreSQL with async SQLAlchemy, append-only audit trail, and Razorpay webhook endpoint (`POST /api/webhooks/razorpay`). |
| **Merchant Dashboard** | **100% Real** | Next.js 14 dashboard with live aging filters, interactive WhatsApp simulator, and audit log inspector. |
| **Buyer Response Dynamics** | **Modeled** | Driven by a shared, neutral credit-risk and fatigue model (`shared_should_settle` in `baselines.py`) across a held-out test split ($n=71$). |
| **WhatsApp Delivery** | **Simulated Transport** | Simulated outbound/inbound delivery logged to the database and visualized in the interactive inbox. Real WhatsApp Business API uses an identical adapter interface. |
| **Razorpay Payment Links** | **Test Mode / Mock Fallback** | Generates authentic test-mode links when API credentials are provided, or deterministic mock URLs (`https://rzp.io/l/...`) for offline local runs. Never initiates direct debits. |

---

## Evaluation Benchmark & Robustness

Reproducible via `python scripts/run_eval.py` and `python scripts/run_multi_seed_eval.py` driving the **real deterministic engine** across simulated timelines:

### 10-Seed Multi-Seed Robustness (10 Seeds, ~710 Test Invoices, Mean ± Std Dev)

| Strategy | Recovery Rate (%) | Recovered (INR Lakhs) | Avg Days to Recovery | Contacts Sent | Efficiency (₹/Contact) | Disputed Invoices |
|:---|:---|:---|:---|:---|:---|:---|
| `no_agent` (Self-cure only) | 74.4% ± 7.8% | ₹ 70.15L | 5.9 ± 2.0 days | 0.0 ± 0.0 | ₹ 0 / contact | 0.0 touches |
| `naive_cadence` (Blind 7-day loop) | 78.5% ± 6.3% | ₹ 74.12L | 6.3 ± 1.9 days | 55.6 ± 15.3 | ₹ 1,40,531 / contact | Blindly spams (13.4 ± 3.8 touches) |
| **`duebot` (Policy-aware agent)** | **79.3% ± 5.9%** | **₹ 74.92L** | **5.8 ± 1.9 days** | **21.5 ± 6.5** | **₹ 3,79,178 / contact (+170%)** | **Routes to `HUMAN_REVIEW` (0.0 touches)** |

### Key Takeaways:
1. **Real Engine Execution**: DueBot runs its actual state machine (`transition`), policy guard (`can_contact`), and scheduler (`next_action_at`) on every simulated clock tick.
2. **+170% Higher Capital Efficiency (61.3% Fewer Contacts)**: DueBot achieves maximum recovery while sending **61.3% fewer messages** (21.5 vs 55.6 touches) due to weekly frequency caps, sequence limits (3 touches max), and promise-aware pausing.
3. **Dispute Safety & Defect Prevention**: DueBot abstains on disputed invoices (routing to `HUMAN_REVIEW` with 0 touches), preventing the 13.4 spam touches that a blind cadence delivers.
4. **Epistemic Honesty on Speed**: DueBot trends slightly faster (5.8 vs 6.3 days) due to its 3-day adaptive interval, though this difference overlaps within variance (±1.9 days). We present this as an operational dynamic rather than an inflated headline claim.

---

## Merchant Dashboard & UI Features

- **Invoices & Aging**: Dynamic filtering by bucket (0-30, 31-60, 61-90, 90+ days), risk score, and lifecycle state.
- **Invoice Timeline**: Complete interaction history, outbound nudges, and state transitions.
- **Append-Only Audit Viewer**: Full immutability for compliance and accounting.
- **Simulated WhatsApp Inbox**: Live interactive interface for evaluating promise extraction and human fallback routing.
- **Optional Voice Briefing**: Interactive voice briefing using browser Web Speech API & LLM synthesis for hands-free merchant portfolio review.

---

## Design Decisions (Why This, Not That)

| Choice | Why |
|--------|-----|
| Hand-rolled state machine | Legible under interview; no LangChain agent loop for money-adjacent actions |
| Postgres / SQLite | Structured invoices/promises/audit — not a retrieval problem |
| Poll loop / task triggers | Throughput does not justify distributed queue overhead |
| Claude / Gemini tool-use | Strict schema enforcement; never regex-parse model prose |
| Razorpay Payment Links | Non-custodial; requests payment without auto-debits |

---

## Verification & CI

Automated checks run on every push via GitHub Actions (`.github/workflows/ci.yml`):

```bash
# Formatting & linting
ruff check backend tests scripts

# Strict static type checking
mypy --strict backend

# Complete unit, integration, and eval test suite
pytest tests/unit tests/integration tests/eval -v
```
