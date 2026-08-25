# DueBot

An AI collections agent for overdue **B2B receivables**, built for the Razorpay AI Buildathon 2026 (Track 03 — AI Revenue Recovery).

DueBot watches a merchant's overdue invoices, decides **when** to nudge (WhatsApp-first, hard contact caps), parses buyer replies into structured intents, tracks promise-to-pay dates, and escalates when a promise breaks — or when the model is not confident. It **never moves money**. It only requests payment via Razorpay Payment Links. Every state transition is an append-only audit row.

**DueBot** is a production-grade autonomous collections agent for overdue B2B receivables: deterministic core, LLM periphery, comprehensive test suite, and an empirical three-way baseline evaluation — not a chatbot wrapper.

## Architecture (one diagram)

```mermaid
flowchart LR
  UI[Next.js dashboard]
  API[FastAPI]
  ENG[engine: aging risk policy states]
  LLM[llm: parse + draft]
  DB[(Postgres)]
  UI --> API --> ENG
  API --> DB
  API --> LLM
  LLM -->|"structured intent + confidence"| ENG
```

The LLM never decides whether to act. `engine/policy.py` and `engine/states.py` do.

Full design: [ARCHITECTURE.md](ARCHITECTURE.md). Demo script: [docs/DEMO_SCRIPT.md](docs/DEMO_SCRIPT.md). FAQ: [docs/DESIGN_FAQ.md](docs/DESIGN_FAQ.md). Eval: [docs/EVALUATION_METHODOLOGY.md](docs/EVALUATION_METHODOLOGY.md).

## Quickstart

```bash
python -m pip install -e ".[dev]"
copy .env.example .env
```

For a laptop demo without Postgres:

```
DATABASE_URL=sqlite+aiosqlite:///./duebot.db
```

```bash
uvicorn backend.main:app --reload --port 8000
python scripts/seed_db.py --num-invoices 80
cd frontend && npm install && npm run dev
```

Generate a dataset only:

```bash
python -m backend.data.generator --num-invoices 260 --seed 42
```

## API (summary)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/health` | Liveness |
| GET/POST | `/api/merchants` | Merchants |
| GET | `/api/invoices` | Filterable list |
| GET | `/api/invoices/{id}` | Timeline + audit |
| POST | `/api/invoices/ingest` | CSV ingest |
| GET | `/api/buyers` | Buyers |
| POST | `/api/nudge/trigger?dry_run=` | Policy → draft → optional send |
| GET | `/api/nudge/preview/{id}` | Never sends |
| GET | `/api/promises` | Promises |
| GET | `/api/audit` | Append-only log |
| GET | `/api/metrics/recovery` | Live DB metrics |
| GET | `/api/metrics/baseline` | Three-way comparison |
| POST | `/api/inbox/reply` | Simulated inbound |
| POST | `/api/seed` | Generator → DB |

Envelope: `{"data": ..., "meta": {"timestamp", "request_id", "total_count"}}`.

## Merchant Dashboard & Live Demo UI

The Next.js 14 frontend provides a real-time merchant control center:

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│ DueBot Collections Dashboard                     [ Seed DB ]  [ Trigger Nudge ] │
├────────────────────────┬────────────────────────┬───────────────────────────────┤
│ Receivables at Risk    │ Recovery Rate          │ Promise Kept Rate             │
│ ₹ 85,95,033            │ 95.8% (+17.6% vs Naive)│ 28.6% (Strict Audit)          │
├────────────────────────┴────────────────────────┴───────────────────────────────┤
│ AGING BUCKETS                                                                   │
│ [ 0-30 Days: 38% ]  [ 31-60 Days: 29% ]  [ 61-90 Days: 18% ]  [ 90+ Days: 15% ]   │
├─────────────────────────────────────────────────────────────────────────────────┤
│ SIMULATED WHATSAPP INBOX                                                        │
│ "I can pay ₹25,000 on Friday" ➔ Intent: PROMISE ➔ State: PROMISED               │
└─────────────────────────────────────────────────────────────────────────────────┘
```

- **Invoices & Aging**: Dynamic filtering by bucket, risk score, and lifecycle state.
- **Invoice Timeline**: Complete interaction history, outbound nudges, and state transitions.
- **Append-Only Audit Viewer**: Full immutability for compliance and accounting.
- **Simulated WhatsApp Inbox**: Live interactive demo for evaluating promise extraction and human fallback routing.

## Evaluation (held-out generator `test` split, seed=42, n=71)

Executed via `python scripts/run_eval.py` driving the **real deterministic engine** (`can_contact`, `transition`, `next_action_at`, `fallback_intent`) — zero fixture stubs:

| Strategy | Recovery Rate | Total Recovered (INR) | Avg Days to Recovery | Contacts Sent | Recovery / Contact (Capital Efficiency) | Disputed Invoices |
|----------|---------------|-----------------------|----------------------|---------------|---------------------------------|-------------------|
| `no_agent` (Self-cure only) | 73.5% | ₹ 66,00,741 | 8.3 days | 0 | ₹ 0 / contact | 0 contacts |
| `naive_cadence` (Blind 7-day interval) | 79.8% | ₹ 71,62,421 | 8.6 days | 48 | ₹ 1,49,217 / contact | Blindly spams (8 contacts) |
| **`duebot` (Policy-aware agent)** | **79.8%** | **₹ 71,62,421** | **8.1 days** | **15** | **₹ 4,77,495 / contact (+220%)** | **Routes to `HUMAN_REVIEW` (0 contacts)** |

### Key Takeaways:
1. **Real Engine Execution**: DueBot runs its actual state machine (`transition`), policy guard (`can_contact`), and scheduler (`next_action_at`) on every simulated clock tick.
2. **+220% Higher Capital Efficiency (₹ 4.77L vs ₹ 1.49L / contact)**: DueBot achieves maximum recovery while sending **68.8% fewer contacts** (15 vs 48) due to weekly frequency caps, sequence limits (3 touches max), and promise-aware pausing.
3. **Faster Emergent Cash Resolution (8.1 vs 8.6 days)**: Driven naturally by DueBot's 3-day adaptive interval vs Naive's static 7-day timer.
4. **Dispute Safety & Zero Spam**: DueBot abstains on disputed invoices (routing to `HUMAN_REVIEW` with 0 contacts) and enforces a hard contact cap (max 3/week).

## Design decisions (why this, not that)

| Choice | Why |
|--------|-----|
| Hand-rolled state machine | Legible under interview; no LangChain agent loop for money-adjacent actions |
| Postgres | Structured invoices/promises/audit — not a retrieval problem |
| Poll loop | Throughput does not justify a queue |
| Claude tool-use only | Never regex-parse model prose |
| Simulated WhatsApp | Demo-safe; real Business API is a documented swap |

## Verification & CI

Automated checks run on every push via GitHub Actions (`.github/workflows/ci.yml`):

```bash
ruff check backend tests
mypy --strict backend
pytest tests/unit tests/integration tests/eval -v
```
