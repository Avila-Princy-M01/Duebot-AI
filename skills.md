# DueBot — AI Coding Assistant Rules

> **Read this file before writing any code in this repository.**
> This is the single source of truth for architecture, conventions, and quality bar.
> Violating these rules is worse than writing no code at all.

---

## 0. What This Project Is

**DueBot** is an AI-powered B2B receivables recovery agent built for the Razorpay AI Buildathon 2026 (Track 03: AI Revenue Recovery).

- **It chases overdue B2B invoices** via WhatsApp/email nudges on behalf of SME merchants.
- **It tracks buyer payment promises** (promise-to-pay) and escalates when promises break.
- **It never moves money.** It only requests payment via Razorpay Payment Links.
- **Every action is bounded, logged, and reversible.** The audit log is a first-class deliverable.

This is a hiring evaluation, not a demo competition. The judges are Razorpay engineers who will read every line of code. Write code that looks like it was shipped to production, not thrown together for a hackathon.

---

## 1. Architecture Principles

### 1.1 Deterministic Core, LLM Periphery

The system has two layers. Do not blur them.

| Layer | What | How | Why |
|-------|------|-----|-----|
| **Deterministic engine** | Invoice aging, risk-tier classification, contact-frequency caps, escalation rules, state transitions, audit logging | Plain Python functions, pure logic, no API calls | Compliance, predictability, testability. A judge should be able to read the state machine and trace any decision back to a rule. |
| **LLM-assisted layer** | Message personalization (tone within template envelope), free-text buyer reply parsing (extract promise/objection/dispute intent) | Claude Sonnet via Anthropic API, function-calling for structured output | These are genuine language tasks. The LLM never decides *whether* to act — only *how to phrase* or *what the buyer said*. |

**Rule:** If a feature can be implemented deterministically, it must be. The LLM is a last resort for language tasks, not a crutch for missing logic.

### 1.2 State Machine Over Framework

The invoice lifecycle is a finite state machine. Model it explicitly.

```
States: CREATED → OVERDUE → NUDGED → REPLIED → PROMISED → REMINDED → RECOVERED
                                                              ↘ DISPUTED → HUMAN_REVIEW
                                                              ↘ ESCALATED → HUMAN_REVIEW
                                                              ↘ OPTED_OUT → TERMINATED
```

- Every state transition is an append-only audit log row: `(invoice_id, from_state, to_state, actor, timestamp, reasoning_summary)`.
- State transitions are triggered by deterministic conditions (days overdue, reply parsed intent, policy thresholds), never by LLM output directly.
- The LLM output (parsed intent) is *fed into* the state machine as an input — the state machine decides what to do with it.

### 1.3 Safety-First Design

DueBot is a collections tool. The blast radius of a bug is reputation damage and buyer relationships, not just money. Design for this.

**Hard invariants (never violate, no matter what the LLM says):**
- Max 3 contacts per invoice per week (configurable, but default cap).
- No contact after explicit buyer opt-out — honor immediately, irreversibly.
- No discount, waiver, or write-off offered without human approval.
- No auto-debit — only payment link generation.
- Disputed invoices are immediately escalated to human; never nudged.
- Every message is logged *before* send, with content + channel + recipient.

**Soft guardrails (log violations, flag for human, don't hard-block):**
- Reply-parsing confidence below threshold → flag for human confirmation.
- Buyer sends contradictory signals (promises then disputes) → escalate.
- Contact frequency approaching cap → warn in dashboard.

### 1.4 No Over-Engineering

This is a hackathon project that must look professional. That means clean, not complex.

- **No message queue** — a simple poll/cron loop is honest and sufficient.
- **No vector database** — this is structured state tracking, not retrieval.
- **No microservices** — a monolith with clean module boundaries is the right call.
- **No Kubernetes/Docker orchestration** — deploy on Vercel + Railway/Render.
- **No LangChain/CrewAI/AutoGen** — a hand-rolled state machine + direct API calls is more defensible in an interview than a black-box framework. When the judge asks "why this framework?", the answer "I didn't need one — here's why" is stronger than "I used LangGraph because..."
- **No Redis** — Postgres is the only data store needed at this scale.
- **No GraphQL** — REST is fine, simpler, and faster to build.

---

## 2. Tech Stack (Non-Negotiable)

| Layer | Choice | Why |
|-------|--------|-----|
| **Frontend** | Next.js 14+ (App Router) + Tailwind CSS | Fast to build, judge-familiar, excellent DX |
| **Backend** | Python 3.11+ with FastAPI | Clean for both deterministic logic and LLM calls |
| **Database** | PostgreSQL (via SQLAlchemy async + Alembic) | Structured data, migrations, JSONB for flexible fields |
| **ORM** | SQLAlchemy 2.0+ (async) | Type-safe, well-typed, modern Python |
| **Migrations** | Alembic | Version-controlled schema |
| **LLM** | Claude Sonnet via `anthropic` Python SDK | Matches Razorpay's own stack; function-calling for structured output |
| **Payments** | Razorpay SDK (test mode) — Payment Links, Invoices, Orders | The product IS a Razorpay integration |
| **Validation** | Pydantic v2 models | Request/response validation, typed configs |
| **Testing** | pytest + pytest-asyncio + httpx (for FastAPI test client) | Industry standard |
| **Linting** | Ruff (replaces flake8 + isort + black) | Fast, opinionated, single tool |
| **Type checking** | mypy with strict mode | Non-negotiable for impressing judges |
| **Env management** | `pyproject.toml` + `uv` or `pip-tools` | No `requirements.txt` sprawl |

**Do NOT introduce any library not listed here without explicit justification.** Check if the project already uses it before adding a new dependency.

---

## 3. Project Structure

```
duebot/
├── README.md                          # 300+ lines, includes setup, architecture, metrics
├── ARCHITECTURE.md                    # Detailed system design (separate from README)
├── .env.example                       # All required env vars with descriptions
├── pyproject.toml                     # Single source of truth for deps, scripts, tools
├── alembic.ini
│
├── backend/
│   ├── __init__.py
│   ├── main.py                        # FastAPI app factory
│   ├── config.py                      # Pydantic Settings (env-driven, no hardcoded values)
│   ├── dependencies.py                # FastAPI dependency injection
│   │
│   ├── models/                        # SQLAlchemy ORM models
│   │   ├── __init__.py
│   │   ├── merchant.py
│   │   ├── buyer.py
│   │   ├── invoice.py
│   │   ├── interaction.py
│   │   ├── promise.py
│   │   └── audit_log.py
│   │
│   ├── schemas/                       # Pydantic request/response schemas
│   │   ├── __init__.py
│   │   ├── merchant.py
│   │   ├── buyer.py
│   │   ├── invoice.py
│   │   ├── interaction.py
│   │   └── promise.py
│   │
│   ├── api/                           # FastAPI route handlers
│   │   ├── __init__.py
│   │   ├── merchants.py
│   │   ├── invoices.py
│   │   ├── buyers.py
│   │   ├── nudge.py
│   │   ├── promises.py
│   │   ├── audit.py
│   │   └── health.py
│   │
│   ├── engine/                        # Core business logic (NO API calls, NO LLM)
│   │   ├── __init__.py
│   │   ├── states.py                  # Invoice state machine (states + transitions)
│   │   ├── aging.py                   # Invoice aging calculator
│   │   ├── risk_tier.py              # Buyer risk classification (deterministic)
│   │   ├── policy.py                  # Contact caps, opt-out rules, escalation thresholds
│   │   ├── scheduler.py              # Nudge scheduling logic (when to contact next)
│   │   └── recovery_metrics.py       # Recovery rate calculation, baseline comparison
│   │
│   ├── llm/                           # LLM integration (the ONLY place LLM is called)
│   │   ├── __init__.py
│   │   ├── client.py                  # Anthropic client wrapper (retry, timeout, logging)
│   │   ├── reply_parser.py           # Parse buyer free-text → structured intent
│   │   ├── message_drafter.py        # Draft nudge messages within template envelope
│   │   ├── prompts/                   # Prompt templates (version-controlled, not inline)
│   │   │   ├── reply_parsing.py
│   │   │   └── message_drafting.py
│   │   └── types.py                   # Pydantic models for LLM input/output
│   │
│   ├── integrations/                  # External service clients
│   │   ├── __init__.py
│   │   ├── razorpay.py               # Razorpay SDK wrapper (Payment Links, Invoices)
│   │   ├── whatsapp.py               # WhatsApp Business API (or simulated inbox)
│   │   └── email_sender.py           # Email fallback
│   │
│   ├── tasks/                         # Background tasks (simple polling, no Celery)
│   │   ├── __init__.py
│   │   ├── aging_checker.py          # Periodic invoice aging scan
│   │   ├── nudge_executor.py         # Send pending nudges
│   │   ├── promise_checker.py        # Check for broken promises
│   │   └── reply_processor.py        # Process incoming replies
│   │
│   └── data/                          # Synthetic data generation + seeding
│       ├── __init__.py
│       ├── generator.py              # Synthetic invoice/buyer/merchant generator
│       ├── seed.py                    # Seed DB with synthetic data
│       └── baselines.py              # Naive retry baseline for comparison
│
├── frontend/                          # Next.js app
│   ├── package.json
│   ├── next.config.js
│   ├── tailwind.config.js
│   ├── tsconfig.json
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx                   # Dashboard landing
│   │   ├── invoices/
│   │   │   ├── page.tsx               # Invoice list with aging buckets
│   │   │   └── [id]/page.tsx          # Single invoice timeline
│   │   ├── buyers/
│   │   │   ├── page.tsx               # Buyer risk profiles
│   │   │   └── [id]/page.tsx          # Single buyer history
│   │   ├── audit/
│   │   │   └── page.tsx               # Immutable audit log viewer
│   │   ├── metrics/
│   │   │   └── page.tsx               # Recovery metrics + baseline comparison
│   │   └── api/                       # Next.js API routes (thin proxy to backend)
│   ├── components/
│   │   ├── dashboard/
│   │   │   ├── AgingBuckets.tsx
│   │   │   ├── RecoveryChart.tsx
│   │   │   ├── BaselineComparison.tsx
│   │   │   └── MetricCards.tsx
│   │   ├── invoices/
│   │   │   ├── InvoiceTimeline.tsx
│   │   │   └── InvoiceTable.tsx
│   │   ├── audit/
│   │   │   └── AuditLog.tsx
│   │   └── ui/                        # Shared UI primitives (Button, Card, etc.)
│   ├── lib/
│   │   ├── api.ts                     # API client (typed fetch wrapper)
│   │   └── types.ts                   # TypeScript types matching backend schemas
│   └── public/
│
├── tests/
│   ├── conftest.py                    # Shared fixtures (test DB, test client, mock LLM)
│   ├── unit/
│   │   ├── test_aging.py
│   │   ├── test_risk_tier.py
│   │   ├── test_policy.py
│   │   ├── test_states.py
│   │   └── test_reply_parser.py
│   ├── integration/
│   │   ├── test_razorpay.py
│   │   └── test_nudge_flow.py
│   └── eval/                          # Evaluation harness (the credibility layer)
│       ├── run_eval.py                # Run held-out eval batch
│       ├── report.py                  # Generate comparison report
│       └── fixtures/                  # Test fixture data
│
├── scripts/
│   ├── setup.sh                       # One-command project setup
│   ├── seed_db.py                     # Seed database
│   └── run_eval.py                    # Run evaluation
│
└── docs/
    ├── DEMO_SCRIPT.md                 # 5-minute pitch script (Part J)
    ├── JUDGE_FAQ.md                   # 20 anticipated questions + answers
    └── EVALUATION_METHODOLOGY.md      # How metrics are calculated
```

---

## 4. Code Style & Conventions

### 4.1 Python

- **Formatter/Linter:** Ruff. Run `ruff format .` and `ruff check . --fix` before every commit.
- **Type hints:** Required on all function signatures, class attributes, and variables. mypy strict mode must pass.
- **Docstrings:** Google style. Every public function/class/module must have one. Internal helpers can skip.
- **Imports:** Sorted by Ruff (isort-compatible). Group: stdlib → third-party → local. No wildcard imports.
- **Naming:**
  - `snake_case` for functions, variables, modules.
  - `PascalCase` for classes, Pydantic models, enums.
  - `UPPER_SNAKE_CASE` for constants.
  - Private methods: `_leading_underscore`. No double-underscore name mangling.
- **Error handling:** Specific exceptions, never bare `except:`. Create domain exceptions in `backend/exceptions.py`.
- **No magic numbers.** Named constants with units: `MAX_CONTACTS_PER_WEEK = 3`, not `if attempts < 3`.
- **No global mutable state.** Use dependency injection via FastAPI's `Depends()`.
- **Async by default.** All DB calls, API calls, and I/O must be async. Sync functions only for pure computation.

### 4.2 TypeScript / React

- **Formatter:** Prettier. Linter: ESLint. Run both before commit.
- **Strict mode:** `tsconfig.json` with `strict: true`, `noUncheckedIndexedAccess: true`.
- **Components:** Functional only. No class components. Named exports only (no default exports).
- **Props:** Defined with `interface` (not `type`) at the top of each component file.
- **State:** Local state for UI concerns. No global state library (no Redux/Zustand) — this is a dashboard, not a SPA.
- **Styling:** Tailwind CSS only. No CSS modules, no styled-components, no inline styles.
- **API calls:** Through the typed `lib/api.ts` wrapper. Never raw `fetch` in components.
- **Error boundaries:** Wrap each page in an error boundary component.

### 4.3 Git Conventions

- **Commit messages:** Conventional Commits format: `feat(invoices): add aging bucket calculation`, `fix(policy): cap contact frequency correctly on boundary`.
- **Branch naming:** `feat/short-description`, `fix/short-description`, `eval/add-baseline-comparison`.
- **No force pushes** to main. No rewriting history.
- **Every commit must pass** `ruff check`, `mypy --strict`, `pytest`, and `next build`.
- **Squash merge** feature branches into main.

### 4.4 Documentation

- **README.md:** Must include (1) one-paragraph project description, (2) architecture diagram (ASCII or Mermaid), (3) quickstart (copy-paste setup), (4) API reference summary, (5) evaluation results, (6) design decisions (why this, not that).
- **Every module:** Has a module-level docstring explaining its role.
- **Every public function:** Has a docstring with Args, Returns, Raises.
- **`.env.example`:** Every env var with a description. No undocumented configuration.
- **Architecture decisions:** Log significant choices in `docs/` as ADRs (Architecture Decision Records).

---

## 5. Testing Standards

### 5.1 Coverage Targets

| Area | Min Coverage | What |
|------|-------------|------|
| `engine/` | 95%+ | This is the deterministic core. Every state transition, every policy rule, every edge case. |
| `llm/` | 80%+ | Mock the API call, test prompt construction and output parsing. |
| `api/` | 85%+ | Every endpoint tested for happy path + validation errors + 404s. |
| `integrations/` | 70%+ | Mock external APIs. Test retry logic, error handling, timeout behavior. |
| Overall | 80%+ | Enforced by CI. |

### 5.2 Test Types

- **Unit tests:** Fast, no I/O. Test pure logic in `engine/`, `llm/` (with mocked API), schemas.
- **Integration tests:** Test API endpoints with a test database (SQLite for speed, or test Postgres).
- **Eval tests:** The credibility layer. Run on held-out synthetic data, report precision/recall/recovery-rate. These are NOT unit tests — they're the benchmarks that prove DueBot works.

### 5.3 Test Conventions

- Test file names mirror source: `engine/aging.py` → `tests/unit/test_aging.py`.
- Use `pytest.mark.parametrize` for edge cases.
- Use fixtures in `conftest.py` for shared setup (test DB, test client, mock LLM).
- No test should depend on external services or network access (except explicit integration tests marked with `@pytest.mark.integration`).
- Every test docstring explains WHAT is being tested and WHY.

---

## 6. Security & Safety Rules

### 6.1 Data Handling

- **No PII in logs.** Mask phone numbers, email addresses, invoice amounts in log output.
- **No hardcoded secrets.** All secrets come from environment variables via Pydantic Settings.
- **No SQL injection.** Use SQLAlchemy ORM exclusively. Raw SQL is forbidden.
- **No XSS.** React escapes by default. Sanitize any user-generated content rendered in HTML.

### 6.2 Action Safety

- **DueBot never initiates financial transactions.** It generates Payment Links (which the buyer initiates), never debits.
- **Every outbound communication is logged pre-send.** If the log write fails, the send does not happen.
- **Idempotency:** Every state transition key is `(invoice_id, attempt_number)`. Crashes mid-send are safe — on restart, unresolved states are re-verified before retrying.
- **Audit log is append-only.** No UPDATE or DELETE on the `audit_log` table. Enforce at the DB level if possible.

### 6.3 LLM Safety

- **Structured output only.** Use Claude's function-calling / tool-use to force structured JSON. Never parse free-text LLM output with regex.
- **Confidence thresholds.** If the LLM's parsed intent has confidence below 0.7, flag for human review. Never auto-log a promise the system isn't confident about.
- **Prompt injection defense.** Buyer reply text is treated as untrusted input. Prompts use clear role boundaries. No system prompt leakage.
- **Cost tracking.** Log token usage per LLM call. Set hard budget limits.

---

## 7. Performance Requirements

| Metric | Target | Why |
|--------|--------|-----|
| API response time (p95) | < 200ms | Dashboard must feel instant |
| Invoice aging scan | < 5s for 10,000 invoices | Deterministic computation, no excuse for slowness |
| LLM reply parse | < 3s | Acceptable for a language task; show the latency transparently |
| Message send + log | < 2s end-to-end | Must log before send, send is the bottleneck |
| Evaluation batch (200 invoices) | < 60s | The eval harness must run fast for iteration |

---

## 8. What Judges Will Look For (Build For This)

The judges are Razorpay engineers evaluating you for a hiring position. They will check:

1. **Does the state machine work correctly?** Trace an invoice through every state. Every transition must be auditable.
2. **Are the safety invariants actually enforced?** Not just documented — enforced in code, tested, and provable.
3. **Is the LLM used appropriately?** Not as a magic wand. They will ask "why is AI needed here?" and the answer must be specific.
4. **Is the eval honest?** A three-way comparison (no-agent vs. naive vs. DueBot) on a held-out set is infinitely more convincing than cherry-picked results.
5. **Does the code look professional?** README, type hints, docstrings, clean imports, meaningful commit messages.
6. **Can you explain every decision?** The panel interview will probe: "Why Postgres and not a vector DB?" "Why hand-roll instead of using LangChain?" "Why is the retry logic deterministic?" Know the answer.

**The single most impressive thing you can ship:** The live-triggered ambiguous-reply failure case where DueBot correctly refuses to log a false promise, explains why, and hands it to a human. This one demo moment proves bounded/gated/explainable action better than any slide.

---

## 9. Red Lines (Never Do These)

- ❌ Use a global variable for config or state.
- ❌ Catch `Exception` or `BaseException` without re-raising.
- ❌ Use `print()` for logging. Use `structlog` or `logging` module.
- ❌ Hardcode any URL, API key, port, or secret.
- ❌ Add a dependency without documenting it in `pyproject.toml`.
- ❌ Write a test that depends on execution order.
- ❌ Use `Any` type in Python without a comment explaining why.
- ❌ Make the LLM decide whether to take an action (it can only shape how the action is phrased).
- ❌ Skip the audit log for any state transition.
- ❌ Auto-resolve exceptions in the reconciliation path without confidence thresholds.
- ❌ Add a feature that isn't covered by the data model in `ARCHITECTURE.md`.
- ❌ Commit code that doesn't pass `ruff check`, `mypy --strict`, and `pytest`.
- ❌ Use `TODO` or `FIXME` in committed code without a linked issue.
- ❌ Create files outside the project structure defined in Section 3.
- ❌ Use placeholder/mock data in the eval harness — it must use the real synthetic generator.

---

## 10. File Creation Rules

When creating new files:
1. Follow the directory structure in Section 3 exactly.
2. Every Python file starts with a module docstring.
3. Every TypeScript component is a named export.
4. Every new API endpoint has a Pydantic request/response schema.
5. Every new model has an Alembic migration.
6. Every new function has type hints and a docstring.
7. Every new feature has corresponding tests.
8. Update `ARCHITECTURE.md` if the change affects the system design.

---

## 11. Commit Checklist

Before every commit, verify:

```
ruff format .
ruff check . --fix
mypy --strict backend/
pytest tests/unit/ -v
cd frontend && npm run build
```

All must pass. No exceptions.

---

*This document is the law. When in doubt, re-read it. When you disagree with it, propose a change via PR — don't just violate it.*
