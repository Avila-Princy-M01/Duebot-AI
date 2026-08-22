# Razorpay Buildathon — Winning Strategy Report

*Compiled August 21, 2026. Primary sources cited inline; inferences marked as such.*

---

## ⚠️ Read this first: what this event actually is

Before anything else, one correction to the brief that changes how you should build.

Searching for "Razorpay Buildathon 2026" surfaces one live, official event: the **Razorpay AI Buildathon** at `razorpay.com/buildathon`. It is **not** a weekend hackathon judged by VCs for a cash prize. It is a **student-only hiring funnel for a paid AI Builder Internship** (₹75,000/month, 6 or 12 months, in-person Bangalore, starting September). There is no aptitude test or group discussion — instead: **pick a track → build something real → submit a public GitHub repo + a 5-minute pitch video + an architecture writeup → if it has signal, you get a panel interview.** Applications close **September 5, 2026**. The five tracks (01–05) match your brief's descriptions verbatim.

This matters for strategy in three concrete ways:

1. **The judges are Razorpay engineers/PMs conducting a hiring evaluation, not investors judging a pitch competition.** They will read your code, question your architecture decisions ("why this vector store, why this model, why this framework"), and check whether your repo looks like professional work — README, commit history, setup docs — not just whether the demo video is flashy.
2. **There is no large public GitHub graveyard of "Razorpay Buildathon" submissions to differentiate against yet** — the event is upcoming, not concluded. Your GitHub competitive analysis has to look at the *adjacent* space (chargeback agents, dunning/recovery agents, reconciliation tools) rather than literal past entries, because none exist publicly yet.
3. **The real competitor you must differentiate against is not other students. It's Razorpay's own shipped product.** This is the single most important finding of this research (Part B) — Razorpay has already launched a production "Agent Studio" with 8 live agents that overlap heavily with the track examples. Building one of those, even well, reads as "you didn't do your homework."

Everything below is built around these three facts.

---

## PART A — Competitive Intelligence Summary

The three things worth knowing before you pick an idea:

- **Razorpay already ships agentic products in exactly these problem spaces** (see Part B). Several "example directions" listed in the official track copy are literal names of things Razorpay launched in March–May 2026.
- **The GitHub landscape for generic "AI agent + payments" work is saturated at the demo layer** (dispute-letter drafters, reconciliation scripts, dunning bots) but **thin at the verification/evaluation layer** — almost nobody publishes precision/recall, recovery-rate-on-a-batch, or a reproducible eval harness. This is your wedge (Part E/F).
- **India's payment-failure economics are unusually well-documented and unusually addressable with synthetic data**: UPI AutoPay failure rates (8–15%, vs 2–3% for card mandates)<cite index="81-1">UPI AutoPay failure rates run 8–15%, compared to 2–3% for card mandates</cite>, mandate revocations running ~20 million/month on insufficient balance<cite index="85-1">The revocations stand at 20 million every month…There is a debit execution failure which is because there is not enough money in the user's bank account</cite>, and involuntary churn representing <cite index="78-1">30–40% of subscription churn for Indian SaaS</cite>, with most of it recoverable. These are real, citable, and gettable-as-synthetic-data numbers — exactly what Track 03 wants.

---

## PART B — Razorpay Strategic Landscape

### B.1 What Razorpay already has (confirmed, shipped)

At **FTX'26** (mid-March 2026), Razorpay launched two things simultaneously, both built on **Anthropic's Claude Agent SDK**<cite index="20-1">Razorpay, India's omnichannel payments and banking platform for businesses, announced the launch of the world's first Agent Studio built using the Claude Agent SDK from Anthropic at the FTX 2026 event</cite>:

**1. Razorpay Agent Studio** — <cite index="26-1">a B2B agent marketplace and builder platform for payments and business banking</cite>, debuting with **eight production-ready agents**<cite index="48-1">Razorpay launched eight agents at FTX 2026: Dispute Responder, Subscription Recovery (with ElevenLabs voice), two variants of Abandoned Cart Conversion (SuperU and Nugget by Zomato), Cashflow Forecaster, RTO Shield, RTO Insights, and Settlement Insights</cite>:

| Shipped agent | What it does | Overlaps your track |
|---|---|---|
| **Dispute Responder** | <cite index="24-1">Auto-responds to chargebacks with optimized evidence to maximize dispute win rates</cite> | Track 02 "Chargeback evidence responder" — **directly named** in the track brief |
| **Subscription Recovery** | <cite index="24-1">Analyzes failed subscription payments, applies smarter retry logic, and triggers targeted customer nudges</cite>, built with ElevenLabs for voice | Track 03 "Failed-subscription recovery" and "Hinglish voice recovery" — **both directly named** |
| **Abandoned Cart Conversion** (×2 variants) | Engages checkout-abandoners via voice/messaging, can apply loyalty discounts | Track 03 "Checkout drop-off recovery" — **directly named** |
| **RTO Shield** | <cite index="46-1">Detects high-risk COD orders before dispatch using LLM address validation and bad pincode intelligence</cite> | Track 02 "Return-risk scorer" (COD-specific slice) |
| **RTO Insights** | <cite index="46-1">Analyzes RTO patterns across pincodes, products, and customers to identify preventable return drivers</cite> | Adjacent to Track 02 |
| **Cashflow Forecaster** | <cite index="46-1">Predicts cash position 3–7 days ahead with alerts for payroll risk, shortfalls, and payout failures</cite> | Track 04 "Forward cash forecaster" — **directly named** |
| **Settlement Insights** | <cite index="46-1">Sends a daily settlement summary via WhatsApp to track payouts without checking dashboards</cite> | Adjacent to Track 04 |

**2. Razorpay Agentic Experience Platform** — a conversational layer over the dashboard with three capabilities<cite index="60-1">Agentic Onboarding reduces merchant onboarding time from 30 to 45 minutes to approximately five minutes... The Agentic Dashboard enables merchants to manage payment operations through natural language, for example, uploading a bank statement and requesting an instant reconciliation against Razorpay settlements. Agentic Integration allows merchants, partners, and developers to integrate Razorpay in under ten minutes across AI coding environments</cite>. A later update (the "Agentic Platform," April 2026) added:
- **Intelligent Reconciliation**: <cite index="56-1">upload a screenshot of your bank statement, the agent extracts UTR numbers and amounts instantly, cross-referencing them against Razorpay records to flag discrepancies</cite> — this is **Track 04's "multi-source reconciliation" example, already shipped**.
- **Active Revenue Recovery**: <cite index="56-1">upload a screenshot of a customer's complaint, the agent finds the transaction, identifies why the bank declined it, and suggests a fix</cite>, with **Autonomous Guardrails** for rule-based auto-triggering — this is **Track 03's core loop, already shipped, including the bounded/policy-gated framing your brief asks for**.

There is also a standing, always-on **AI fraud-security agent**: <cite index="21-1">Every transaction on Razorpay is now monitored by an AI security agent that analyses whether a transaction's pattern matches known fraud signatures and blocks suspicious activity before it completes... this agent never sees raw financial data beyond what is required, and all actions occur within the guardrails of the merchant's consent settings</cite> — plus a fraud model described elsewhere in Razorpay's own marketing as <cite index="23-1">reduce fraud-related chargebacks on card payments using insights from 10M+ international cards & 2B+ transaction data points</cite>.

Developer surface: <cite index="21-1">Razorpay provides 400+ documented API endpoints, a Model Context Protocol (MCP) server for LLM-agent integration, and an llms.txt in the developer docs for AI coding tools</cite>, plus one-click payment nodes for n8n/Replit/Vercel and a no-code agent builder (Agent Studio "build your own agent"<cite index="22-1">Use a prebuilt agent as your foundation and customize it with your workflows, tools, and business logic</cite>).

Other Razorpay Sprint'26 items relevant to gap-finding: **UPI Autopay WhatsApp nudges** ("<cite index="54-1">Improves autopay success by re-engaging customers on WhatsApp with timely reminders and incentive-led nudges. It helps recover failed debits and reduce payment churn</cite>"), **AML risk-prediction** ("<cite index="54-1">Built-in intelligence helps predict Anti-Money Laundering risk early, preventing bank issues and settlement delays</cite>"), instant bank-transfer reconciliation, ₹1 UPI Autopay mandate authorization, and real-time UPI mandate cancellation for refunds.

### B.2 What Razorpay is publicly building toward

- **Agent-to-agent commerce infrastructure.** The buildathon's own Track 01 copy states it outright: <cite index="64-1">NPCI's UAP and the global protocol race (ACP, AP2, x402) make agent-to-agent commerce the open problem of the year, and Razorpay's in-app pilots are already live</cite>. Razorpay is positioning for a world where AI shopping assistants transact directly.
- **A public agent-builder API.** By mid-2026, Razorpay was reported to be moving from a closed agent marketplace to <cite index="47-1">public APIs, allowing developers to build custom agents</cite> — i.e., moving from "Razorpay builds the agents" to "Razorpay is a platform others build agents on." This is a strong signal about what a "real product" pitch should sound like: not a monolithic agent, but something composable on their rails.
- **Verification and audit infrastructure**, not just generation. Razorpay's own "Autonomous Guardrails" language ("<cite index="56-1">You can now set rules that protect your revenue while you sleep</cite>") shows they already think in terms of policy-gated automation — which matches your brief's non-negotiable "bounded + explainable + auditable" requirement closely. A submission that treats this as a checkbox rather than a real design constraint will look naive next to what they've already shipped.

### B.3 Where the gaps genuinely are

Cross-referencing the shipped agent list (B.1) against the track's example directions, here is what's **explicitly listed as a track example but not yet shipped as a named production agent**:

| Track | Named-but-unshipped direction | Confidence gap is real |
|---|---|---|
| 02 | **Abuse-ring / collusion sentinel** (fraud rings across merchants, not single-transaction scoring) | High — nothing in any Razorpay material describes network-level, multi-merchant/multi-account collusion detection |
| 02 | **Fraud-spike detector** (velocity/anomaly detection distinct from per-transaction classification) | Medium — the standing fraud agent is transaction-level, not batch/spike-level |
| 03 | **B2B receivables chaser / invoice collections agent** | High — every shipped Track 03-adjacent agent is B2C (cart, subscription, COD). Nothing addresses overdue B2B invoices |
| 03 | **UPI mandate retry *sequencing*** (as distinct from Subscription Recovery's general "smarter retry logic") — i.e., an agent that reasons about *when* in the NPCI retry window and *which channel* to re-attempt, given the ₹1-lakh/₹15k caps and AFA rules | Medium-high — Razorpay's WhatsApp nudge feature is a channel, not a sequencing/timing policy engine |
| 03 | **Promise-to-pay tracker** (customer commits "I'll pay Friday," system tracks and follows up on the commitment specifically) | High — not mentioned anywhere in Razorpay materials |
| 04 | **Tax-line matcher** (GST reconciliation specifically) | High — Intelligent Reconciliation is bank-statement-to-settlement; nothing GST-specific is mentioned |
| 04 | **Settlement Q&A as a distinct evaluated product** (not just a WhatsApp digest) | Medium |

**What we must NOT build:** Dispute Responder (Track 02 chargeback direction, as a generic response drafter), Subscription Recovery, Abandoned Cart Conversion, Cashflow Forecaster, or "upload a bank statement, get instant reconciliation" — all shipped, named, and demoed by Razorpay already at a scale a hackathon build cannot match on data or polish. Building any of these as a close copy is the single most common failure mode a judge from Razorpay will spot in five seconds — because it's their own product.

---

## PART C — GitHub / Builder Landscape

Because the buildathon itself hasn't happened yet (applications close Sept 5), there is no corpus of literal "razorpay-buildathon" submissions to mine. The real competitive surface is the **adjacent open-source and blog landscape** for the same problem classes:

**What everyone is building (saturated):**
- **LLM-drafts-the-dispute-letter tools.** A representative pattern: <cite index="76-1">gather transaction record, fulfillment proof, customer communications, delivery confirmation... prompt the LLM to use only the provided facts... a human reviews and submits</cite>. This exact "context → prompt → draft → human submits" pattern appears repeatedly across Stripe/Paystack-adjacent tooling. It is a wrapper: no measured win-rate, no held-out test set, no adversarial evaluation of drafted evidence quality.
- **Reconciliation dashboards.** e.g., a Shopify↔Razorpay reconciler that <cite index="57-1">segregates Razorpay data into credit and debit records, uses dynamic filtering... matches sales records from Shopify with Razorpay using payment references</cite> and produces charts. Functional but purely deterministic matching with a Streamlit UI — no exception-handling intelligence, no confidence scoring, no LLM reasoning over ambiguous matches.
- **Generic "awesome AI agents" framework lists and agent orchestration boilerplate** (LangGraph/CrewAI/AutoGen style repos) — high volume, zero domain specificity to payments.
- **Payment-gateway SDK wrappers** (django-payments-style integrations) — plumbing, not products.

**What almost nobody is building (this is the actual opportunity):**
- **Anything with a held-out test set and reported precision/recall/false-positive-cost.** The chargeback-tooling space is full of "draft a letter" demos and empty of "here is our win-rate on 200 labeled disputes, and here is what we get wrong and why."
- **Anything that treats *stopping* as a first-class feature** — escalation, abstention, rollback, idempotency. Every reconciliation/recovery tool found treats "the agent acted" as success. None model "the agent correctly refused to act, or correctly escalated."
- **B2B receivables / invoice-chasing agents for the Indian SME context** specifically — the dunning-agent literature is overwhelmingly US-subscription-SaaS-flavored (Stripe/Recurly/Baremetrics benchmarks); the India-specific version (GST invoices, WhatsApp-first collections, promise-to-pay culture) is essentially unaddressed in public repos.
- **Mandate-retry timing/sequencing logic that models NPCI's actual constraints** (AFA thresholds, ₹15k/₹1-lakh caps by category, revocation windows) rather than generic "smart retry" (exponential backoff copied from Stripe's card-retry playbook, which doesn't map to UPI's stateless, cap-bound mechanics).

---

## PART D — Web/Market Pain (with sourcing)

Five specific, well-evidenced merchant pains, evaluated against your ten questions:

### D.1 Involuntary subscription/mandate churn (India-specific)
1. **Who:** Any Indian SaaS/D2C subscription merchant on UPI AutoPay or card e-mandates.
2. **How frequently:** UPI AutoPay failure rate <cite index="81-1">runs 8–15%, compared to 2–3% for card mandates</cite>; initial mandate success sits at only <cite index="80-1">30–50%</cite>; card e-mandate failures spike to <cite index="79-1">20%+ in some categories</cite> after RBI's additional-authentication rule; mandate revocations run <cite index="85-1">20 million every month</cite> nationally, largely on insufficient balance.
3. **How expensive:** <cite index="78-1">Involuntary churn (failed renewal, not user cancellation) is 30–40% of subscription churn for Indian SaaS</cite>, and <cite index="80-1">an Indian SaaS at ₹40L MRR isn't losing 3–6% like a US Stripe business — they're losing 8–15% before any recovery attempt</cite>.
4. **Solved today by:** manual retry configs, generic email dunning, or Razorpay's own Subscription Recovery agent (shipped — see Part B) and WhatsApp nudges.
5. **Why inadequate:** <cite index="78-1">email-only dunning: emails to Gmail land in promotions, recovery rate drops to under 10%</cite>; retry logic copied from card-based playbooks doesn't respect UPI's stateless, cap-bound mechanics.
6. **Why AI helps:** deciding *which channel, which offer, which timing* per failure-reason (insufficient funds vs. mandate expired vs. bank decline) is a genuine reasoning problem, not a fixed cascade.
7. **Why Razorpay specifically:** they hold the mandate lifecycle data, the failure-reason codes, and the settlement ledger — no generic dunning tool can see any of that.
8. **Demonstrable with synthetic data:** yes — failure-reason codes, mandate caps, and retry windows are all public/documented and easy to simulate realistically.
9. **Measurable:** yes — recovery rate, ₹ recovered, time-to-recovery.
10. **Safe to action:** yes, if actions are capped to "resend link / retry within NPCI rules / escalate to human," not silent uncapped retries.

### D.2 Chargebacks / disputes
Visa reported <cite index="71-1">a 30% year-over-year increase in dispute volume between 2023 and 2025</cite>, and <cite index="71-1">for every dispute that reaches a chargeback, the merchant loses the transaction amount, pays a processor fee of $15–$100, and absorbs the operational cost of gathering evidence and responding within tight network deadlines</cite>. Already substantially shipped by Razorpay's Dispute Responder — **do not compete head-on here** unless you add something Razorpay doesn't have (e.g., measured win-rate benchmarking, or abuse-ring correlation across disputes — see F).

### D.3 RTO / COD returns
Large, real, and already the subject of two shipped Razorpay agents (RTO Shield, RTO Insights) reportedly driving <cite index="47-1">18-22% revenue growth</cite> for early adopters (HealthKart, Shadowfax). **Avoid rebuilding; the pre-shipment slice is saturated.** A genuine gap: *predictive* return-risk scoring for **non-COD, non-D2C** contexts (e.g., B2B order returns, marketplace returns) is not covered.

### D.4 B2B receivables / overdue invoices
Not addressed by any shipped Razorpay agent or any Track 03 named example beyond a one-line mention ("B2B receivables chaser"). This is the **cleanest white space** found in this research — real pain (DSO, working-capital drag for Indian SMEs), zero product overlap, zero GitHub saturation, and a natural fit for "detect → diagnose → intervene → recover" per Track 03's own required loop.

### D.5 Reconciliation exceptions
Multi-source reconciliation is genuinely painful and already the subject of Razorpay's "Intelligent Reconciliation" (bank statement → settlement matching). The **exception list itself** — the unmatched, ambiguous, or partially-matched records a reconciler cannot resolve — is under-addressed everywhere: most public tools report a match rate and stop, rather than reasoning about *why* the exceptions exist and recommending a fix. Track 04's own bar ("*an honest exception list... one cherry-picked match proves nothing*") signals Razorpay cares about exactly this.

---

## PART E — White-Space Matrix

Scored 1–10 (10 = best for us). "Already Shipped" = Yes/Partial/No.

| Problem | Existing Solutions | Razorpay Ships It? | GitHub Saturation | Market Pain | AI Leverage | Demo Strength | Measurability | Feasibility | Novelty |
|---|---|---|---|---|---|---|---|---|---|
| B2B receivables / promise-to-pay chaser | Manual, generic dunning SaaS | **No** | 2 | 9 | 8 | 8 | 9 | 8 | 9 |
| UPI mandate retry *sequencing* (policy-aware, not generic backoff) | Generic retry configs | Partial (nudges only) | 2 | 8 | 8 | 8 | 9 | 7 | 8 |
| Reconciliation *exception reasoning* (not matching) | Match-and-report tools | Partial | 3 | 7 | 8 | 7 | 9 | 8 | 8 |
| Fraud-spike / velocity anomaly detector (batch-level, not per-txn) | Rule-based velocity checks | Partial | 4 | 7 | 7 | 6 | 9 | 7 | 6 |
| Abuse-ring sentinel (cross-merchant collusion) | Enterprise fraud suites only | No | 2 | 7 | 8 | 6 | 6 | 5 | 9 |
| Chargeback evidence responder | Razorpay Dispute Responder | **Yes** | 6 | 8 | 6 | 6 | 7 | 8 | 2 |
| Checkout drop-off recovery | Razorpay Abandoned Cart | **Yes** | 7 | 7 | 5 | 5 | 6 | 8 | 2 |
| Subscription recovery (generic) | Razorpay Subscription Recovery | **Yes** | 6 | 7 | 5 | 5 | 6 | 8 | 2 |
| RTO / return-risk (COD) | Razorpay RTO Shield/Insights | **Yes** | 6 | 7 | 5 | 5 | 7 | 7 | 2 |
| Cash forecasting | Razorpay Cashflow Forecaster | **Yes** | 5 | 6 | 5 | 5 | 6 | 6 | 2 |
| Multi-source reconciliation (bank↔settlement match only) | Razorpay Intelligent Reconciliation | **Yes** | 6 | 6 | 5 | 5 | 7 | 7 | 2 |
| Tax-line (GST) matcher | Manual, some ERP plugins | No | 2 | 6 | 6 | 5 | 8 | 6 | 7 |
| Conversational/agent-readable catalog (agent-to-agent commerce) | Early pilots only, no standard yet | Partial (pilots) | 3 | 6 | 7 | 8 | 5 | 5 | 8 |
| Return-risk scoring beyond COD (marketplace/B2B) | None specific | No | 2 | 6 | 6 | 5 | 8 | 6 | 7 |

**Top white spaces (ranked):**
1. B2B receivables / promise-to-pay recovery agent
2. UPI/card mandate retry *sequencing* engine
3. Reconciliation exception-reasoning agent
4. Fraud-spike / velocity anomaly detector with honest FP-cost accounting
5. Abuse-ring / collusion sentinel
6. GST tax-line matcher
7. Agent-readable catalog for agent-to-agent commerce (Track 01, high novelty but low near-term measurability given UAP isn't live yet)
8. Marketplace/B2B return-risk scorer
9. Promise-to-pay tracker as a standalone primitive (could be folded into #1)
10. Settlement Q&A as a rigorously-evaluated product (distinct from Razorpay's WhatsApp digest)

---

## PART F — Rejected Idea Patterns (Fake Novelty)

Per your Phase 5 list, explicitly rejected, with the specific reason tied to this research:

- **"ChatGPT + Razorpay checkout chatbot"** — no differentiation; agent-readable commerce needs a *catalog schema and bounded-action policy*, not a chat wrapper.
- **Generic invoice/reconciliation chatbot** — Razorpay's Agentic Dashboard already does "upload a statement, get reconciliation" in natural language. A chatbot with no exception-handling logic underneath is strictly worse than what's shipped.
- **Basic fraud classifier (single model, single dataset, no FP-cost analysis)** — Track 02's own bar explicitly requires "honest metrics including false-positive cost." A classifier without this is disqualified by the brief itself, not just weak.
- **Ordinary abandoned-cart reminder** — literally shipped as a named Razorpay agent.
- **Chargeback letter generator with no measured win-rate** — this is the single most saturated pattern found in Part C; dozens of near-identical "LLM drafts, human submits" tools exist.
- **LLM wrapper around Razorpay's own APIs with no new reasoning/evaluation layer** — fails the brief's "why is AI uniquely useful here" test.
- **Ordinary reconciliation system that just matches on reference IDs** — this is what `imrexankit/shopify-razorpay` already does on GitHub, deterministically, with charts. Adding an LLM on top without new reasoning about *ambiguous, unmatched, or conflicting* records adds nothing.

---

## PART G — Top 3 Concepts (Deep Design)

Given the volume the full 15-idea/scored matrix would take, this report concentrates depth on the **three strongest, most defensible concepts** — each chosen specifically because it sits in a confirmed white space (Part E, score ≥8 across pain/novelty/measurability) and satisfies every "kill test" in Part H below.

### G.1 — **DueBot** (Track 03: AI Revenue Recovery) — B2B receivables / promise-to-pay recovery agent

**Thesis:** Indian SME B2B sellers lose weeks of working capital to overdue invoices that nobody is systematically chasing — not because collections is hard, but because it's tedious, guilt-laden, and easy to deprioritize. DueBot watches Razorpay-linked invoices, decides *when and how* to nudge (WhatsApp first, escalating tone, never robotic-legal), extracts and tracks explicit promise-to-pay commitments from buyer replies, and escalates to a human the moment a promise breaks or a buyer goes silent past a policy threshold — with every action bounded, logged, and reversible.

**Event → reasoning → action loop:**
`Invoice overdue (T+N days)` → `classify buyer risk (payment history, amount, relationship tenure)` → `select intervention tier (gentle reminder / firm nudge / promise-to-pay ask / escalation)` → `policy check (contact frequency cap, tone rules, spend-none since this doesn't move money, only requests it)` → `send via WhatsApp/email template, LLM-personalized within guardrails` → `parse buyer reply for a promise-to-pay (date + amount)` → `track promise; if broken, escalate tier; if kept, mark recovered` → `audit log every step`.

**Architecture:** React/Next.js merchant dashboard → FastAPI backend → orchestrator (deterministic state machine for the invoice lifecycle; LLM only for (a) message personalization within a template envelope and (b) parsing free-text buyer replies into structured promise/objection/dispute intents) → Postgres for invoice/interaction ledger → Razorpay test-mode Payment Links/Invoices API for generating actual payable links → audit log table, append-only.

**Safety model:** DueBot never moves money — it only *requests* payment via generated links. Hard caps: max 3 contacts/week per invoice, no contact after explicit buyer opt-out, no discount/waiver offered without human approval, escalation-only (never auto-write-off) above a configurable ₹ threshold.

**Metrics:** % of overdue value recovered within 30/60/90 days on a synthetic batch of 200+ invoices; promise-kept rate; time-to-first-contact; false-escalation rate (invoices escalated that would have self-resolved).

**Why judges remember it:** it's the one idea in this whole report with **zero product overlap** with anything Razorpay has shipped, and it's aimed at Razorpay's actual SME base, not glossy D2C.

### G.2 — **MandateIQ** (Track 03/02 hybrid, submit under 03) — Policy-aware UPI/card mandate retry sequencer

**Thesis:** Generic "smart retry" logic is copied from card-network backoff and doesn't understand UPI AutoPay's actual constraints: stateless debits, AFA thresholds, category-specific caps (₹15k/₹1L), and a revocation pattern dominated by insufficient-funds timing (post-salary-credit windows). MandateIQ reasons over the *specific failure reason code* and *account behavior pattern* to choose the retry channel, timing, and amount-splitting strategy — and proves it on a held-out batch.

**Loop:** `mandate debit fails (reason code)` → `diagnose (insufficient funds vs. mandate expired vs. bank decline vs. AFA required)` → `select strategy (retry post-salary-window / re-request mandate / fall back to short payment link / escalate to card e-mandate)` → `policy check (NPCI retry-window rules, max retries/day, no retry after revocation)` → `execute in Razorpay test-mode Subscriptions/Mandate API` → `verify success/failure` → `log + adapt`.

**Evaluation:** recovery rate by failure-reason-code, compared against a "naive fixed-interval retry" baseline on the same synthetic batch — this baseline comparison is the single most convincing thing you can put in front of a judge, because it's a controlled experiment, not a demo.

**Kill-test note:** this is close to Razorpay's shipped "Subscription Recovery" agent. Differentiate hard on: (a) the retry-timing model is *reason-code-specific and empirically compared to a baseline*, which nothing shipped or public does; (b) submit it as an evaluation-first project — the deliverable is the benchmark, not just the agent.

### G.3 — **ReconSense** (Track 04: AI Finance Controller) — Reconciliation exception reasoner

**Thesis:** Every reconciliation tool (Razorpay's included) reports a match rate. Almost none explain *why* the unmatched 5–10% failed to match, or propose a specific, auditable fix per exception (amount rounding, split settlement, currency mismatch, duplicate UTR, timing lag). ReconSense takes a batch of 50+ synthetic multi-source records (bank statement + Razorpay settlement + order system), does deterministic matching first, then uses an LLM *only* to classify and explain the remainder — with a confidence score and a suggested action per exception, never auto-resolving above a policy threshold.

**Loop:** `ingest 3 sources` → `deterministic match (UTR/amount/date, tiered rules)` → `for unmatched: classify exception type` → `propose fix + confidence` → `if confidence > threshold and reversible: apply` → `else: queue for human, explain why` → `report match rate + throughput + honest exception list`.

**Metrics (exactly what Track 04 asks for):** throughput (records/sec), match accuracy on ground truth, exception classification accuracy, % of exceptions correctly auto-resolved vs. correctly escalated (this "correctly escalated" number is the wow-metric almost nobody reports).

---

## PART H — Kill-Test Results (Phase 7)

Applied to all three; summarized:

| Question | DueBot | MandateIQ | ReconSense |
|---|---|---|---|
| Already shipped by Razorpay? | No | Partially (Subscription Recovery) — must differentiate on eval | Partially (Intelligent Reconciliation) — must differentiate on exception reasoning |
| Is AI actually necessary? | Yes — parsing free-text promises and tone-matching nudges is genuinely LLM territory | Partial — the *policy engine* should be deterministic; LLM adds value in the fallback recommendation, not the core retry decision (be honest about this in the pitch) | Yes — exception *classification and explanation* is a language task; matching itself must stay deterministic |
| Could a judge call it a wrapper? | Low risk — the state machine + promise-tracking is real engineering | Medium risk if the baseline comparison is skipped — must include it | Low risk if deterministic-matching-first architecture is shown explicitly |
| Can value be proven? | Yes, on synthetic aging data | Yes, vs. naive-retry baseline | Yes, vs. match-rate-only baseline |
| Simpler deterministic solution exists? | Partially — a cron+CRM could do reminders, but not promise-extraction or tone-adaptive escalation | Partially — but that's the point: showing the *naive* deterministic version underperforms is the demo | Partially — deterministic matching alone gets you 90%; the last 10% is the pitch |
| Would a merchant pay? | Yes — DSO reduction is direct working-capital value | Yes — recovered MRR is a direct, board-visible number | Yes — finance teams' time is the value, well-documented pain |

**Verdict:** DueBot is the strongest — cleanest white space, clearest AI necessity, lowest "you copied our product" risk. MandateIQ and ReconSense are strong #2/#3 but both require an explicit, honest framing ("we compare against Razorpay's approach / a naive baseline, here's what we add") to avoid the wrapper accusation.

---

## PART I — PRODUCT SPEC (Winner)

- **Product name:** DueBot
- **One-line pitch:** An AI collections agent that chases overdue B2B invoices on WhatsApp, tracks buyers' payment promises like a CRM tracks deals, and escalates the moment a promise breaks — every action logged, capped, and reversible.
- **Problem:** Indian SME sellers have real, collectible receivables sitting overdue because collections follow-up is manual, awkward, and gets deprioritized against "real work" — not because buyers refuse to pay, but because nobody chases consistently.
- **Users:** SME finance/ops owners (often the founder) on Razorpay who invoice other businesses (B2B services, wholesale, manufacturing supply).
- **Workflow:** see G.1 loop.
- **Architecture:** Next.js dashboard, FastAPI orchestrator, Postgres ledger, Claude for message personalization + reply parsing (structured JSON output, function-calling for intent extraction), Razorpay test-mode Payment Links + Invoices API, Twilio/WhatsApp Business API sandbox (or a simulated inbox for demo purposes if sandbox access is constrained), append-only audit log.
- **Agent architecture:** deterministic invoice-aging state machine (detection) → deterministic risk-tiering rules using buyer payment history (diagnosis) → LLM-assisted tone/channel selection within a fixed policy envelope (planning) → hard-coded policy engine for contact caps/opt-outs (policy validation) → Razorpay API call to generate/send a payment link, never a debit (action) → webhook/reply-triggered verification (verification) → promise-kept/broken outcome feeds back into buyer risk score (learning).
- **Data model:** `merchants`, `buyers`, `invoices` (amount, due_date, status), `interactions` (channel, message, timestamp, type: nudge/promise/escalation), `promises` (invoice_id, promised_date, promised_amount, status), `audit_log` (append-only, every state transition).
- **APIs:** Razorpay test-mode — Payment Links, Invoices, Orders; optionally Smart Collect for virtual-account matching on the recovery side.
- **Model choices:** Claude Sonnet for reply-parsing (function calling → structured promise/objection/dispute extraction) and message drafting within a template; no fine-tuning needed for a hackathon timeline — prompt + guardrail-tested few-shot examples.
- **Evaluation:** recovery rate at 30/60/90 days vs. a "no-agent" and a "fixed-cadence-email" baseline on a synthetic 200-invoice batch; promise-kept rate; false-escalation rate; average days-to-first-contact.
- **Safety:** contact-frequency cap, no auto-discount/waiver, no auto-write-off, opt-out honored immediately, every message logged pre-send.
- **Audit trail:** every state transition (invoice created → nudge sent → reply parsed → promise logged → promise kept/broken → escalated/recovered) is an immutable row with actor (agent/human), timestamp, and reasoning summary.
- **Failure handling:** if WhatsApp/email delivery fails, retry once then flag for human; if reply-parsing confidence is low, don't auto-log a promise — flag for human confirmation instead of guessing.
- **Metrics:** ₹ recovered / ₹ at risk, days-to-recovery, promise-kept %, escalation precision.

---

## PART J — Demo Script (3–5 minutes)

**0:00–0:30 — The number.** "This synthetic SME has ₹18 lakh in invoices overdue past 30 days. That's real working capital sitting in someone else's bank account." Show the dashboard: aging buckets, total at risk.

**0:30–1:15 — Agent investigates and prioritizes.** DueBot ranks the 40 overdue invoices by expected-recoverable-value × urgency, not just amount. Show the reasoning trace for the top 3: "Buyer A has a 95% on-time history and this is 3 days late — low-touch reminder. Buyer C has missed twice before and this is 45 days late — firm nudge + promise ask."

**1:15–2:15 — Two interventions run live.** One WhatsApp nudge goes out (simulated inbox), buyer replies "will pay Friday" — DueBot parses this into a structured promise, logs it, schedules a follow-up for Saturday if unpaid. A second nudge goes to a buyer who doesn't respond — DueBot escalates per policy after the cap is hit.

**2:15–3:00 — The failure, staged.** Judge (or you) triggers a bad case: a buyer reply that's ambiguous ("will sort it out soon"). DueBot correctly **does not** log a false promise — it flags low confidence and routes to human review, explaining why. This is the moment that proves the system knows its own limits.

**3:00–4:00 — The audit trail and the numbers.** Scroll the immutable log for one invoice end-to-end. Then the dashboard: ₹ recovered this batch, ₹ still at risk, promises kept vs. broken, false-escalation rate on the held-out set, recovery-rate comparison vs. the no-agent baseline.

**4:00–4:30 — The close.** "This isn't a chatbot on top of Razorpay's API. It's a state machine that knows when to talk, what to say, when to stop, and when to admit it doesn't know — with every decision logged. And it's aimed at 10 million SMEs Razorpay already serves, in a space Razorpay hasn't shipped into yet."

---

## PART K — Build Plan

**Must Have:** invoice ingestion (synthetic CSV → Postgres), aging/risk-tier state machine, Razorpay test-mode payment-link generation, one working nudge channel (WhatsApp sandbox or simulated inbox UI), reply-parsing into promise/objection/dispute, promise tracking, contact-cap policy engine, audit log, dashboard with the 4 headline metrics.

**Should Have:** buyer risk scoring from payment history, escalation tiering, a second channel (email fallback), a naive-baseline comparison view side-by-side with DueBot's results.

**Wow Factor:** the live-triggered ambiguous-reply failure case (Part J, 2:15 mark) — this single moment demonstrates bounded/gated/explainable action better than any slide could, and it's cheap to build (it's just a hand-picked test case).

---

## PART L — Tech Stack

- **Frontend:** Next.js + Tailwind (fast to build, judge-familiar, matches frontend-design conventions)
- **Backend:** FastAPI (Python) — clean for both the deterministic state machine and LLM calls
- **Database:** Postgres (SQLite acceptable for a pure hackathon timeline if Postgres setup risks time)
- **Agent framework:** none heavyweight needed — a hand-rolled state machine + direct Claude API calls with function calling is more defensible in a panel interview than a black-box framework ("why this vector store, why this framework" — the honest answer "I didn't need one, here's why" is a strong answer)
- **LLM:** Claude (Sonnet) via Anthropic API — matches Razorpay's own stack choice (Claude Agent SDK), which is a natural talking point in the panel interview
- **Queue:** not needed at this scale; a simple cron/poll loop is honest and sufficient — don't over-engineer
- **Observability:** structured logging to the audit_log table is your observability layer; no need for a separate stack
- **Deployment:** Vercel (frontend) + Railway/Render (backend) or just run locally for the demo — reliability over infra flexing
- **Razorpay APIs:** Payment Links, Invoices, Orders (test mode)

---

## PART M — Synthetic Dataset Design

- **Merchants:** 3–5 synthetic SME profiles (services, wholesale, manufacturing)
- **Buyers:** 40–60 per merchant, with a payment-history distribution (70% reliable, 20% occasional-late, 10% chronic-late)
- **Invoices:** 200+ across merchants, with realistic aging (uniform spread 1–90+ days overdue), amounts (₹5k–₹5L, log-distributed)
- **Labels:** ground-truth "would have paid without intervention" flag (for measuring lift), ground-truth promise outcome (kept/broken/none) for a held-out eval set
- **Injected failures:** ambiguous replies (for the abstention test), a buyer who explicitly opts out mid-sequence, a duplicate invoice, a partial payment
- **Edge cases:** invoice paid *during* the nudge sequence (must detect and stop), buyer who promises then goes silent, disputed invoice (must not chase, must flag)
- **Train/test split:** use 70% of the batch to tune tone/thresholds by hand (not fine-tuning), hold out 30% for the reported eval numbers — be explicit about this in the pitch, since Track 04's own bar warns against "one cherry-picked match."

---

## PART N — Benchmark / Experiment

Compare three conditions on the same held-out 60-invoice set:
1. **No intervention** (baseline recovery rate — what would happen with zero follow-up)
2. **Naive fixed-cadence reminder** (a deterministic "email every 7 days" baseline — cheap to build, essential for credibility)
3. **DueBot**

Report: 30/60/90-day recovery rate for each condition, promise-kept rate, false-escalation rate, average days-to-recovery. This three-way comparison, not the agent alone, is the actual proof of value.

---

## PART O — 20 Judge Questions & Ideal Answers

1. **"Isn't this just Razorpay's Active Revenue Recovery, renamed?"** — No: that feature recovers failed *card/UPI debits* reactively when a merchant uploads a complaint screenshot. DueBot proactively chases *unpaid invoices* (a different object entirely — receivables, not failed transactions) on a schedule, and tracks explicit buyer commitments over time.
2. **"Why not fine-tune a model instead of prompting?"** — No labeled training data exists for this yet; few-shot prompting with a locked template envelope is more auditable and faster to iterate on for a hackathon timeline, and it's what a real MVP would ship with too.
3. **"What happens if the LLM hallucinates a promise that was never made?"** — It can't silently: promise-logging requires a confidence threshold; below it, the system asks the human, never guesses.
4. **"Why is the retry/nudge decision deterministic and not LLM-driven?"** — Because compliance and predictability matter more than cleverness for money-adjacent actions; the LLM's job is language understanding and generation, not policy.
5. **"How do you know your synthetic data isn't unrealistically easy?"** — We deliberately inject ambiguous replies, mid-sequence payments, and opt-outs specifically to stress-test the abstention path.
6. **"What's your false-positive cost here?"** — A false-positive is an escalation on an invoice that would have self-resolved — wastes human attention, not money, since DueBot never auto-collects; low blast radius by design.
7. **"Could this scale to Razorpay's actual merchant base?"** — Yes — the architecture is per-invoice event-driven, horizontally scalable, and the only bottleneck is LLM API throughput on reply-parsing, which is cheap and fast per message.
8. **"Why WhatsApp first?"** — Documented 3× recovery-rate lift over email in the Indian market<cite index="78-1">Dunning: don't email — WhatsApp + UPI link. 3× recovery rate</cite>.
9. **"What's the single most important metric and why?"** — ₹ recovered vs. the naive-baseline delta — it isolates DueBot's actual contribution, not just "did money come in."
10. **"How do you handle a buyer who disputes the invoice instead of promising to pay?"** — Reply-parsing has a `dispute` intent class; disputes never enter the nudge cadence — they're immediately escalated to human, since automated pressure on a disputed invoice is reputationally risky.
11. **"Isn't collections just a CRM feature?"** — A CRM tracks that you *sent* a reminder. DueBot tracks that a buyer *said* something specific and *whether they kept their word* — that's the differentiator, and it's what turns follow-up into forecastable recovery.
12. **"What's your idempotency story if the process crashes mid-send?"** — Every send is a state transition with a unique invoice+attempt key; on restart, unresolved "sending" states are re-verified against the messaging provider before retrying.
13. **"Why not just auto-collect via Razorpay's mandate/autopay instead of asking?"** — B2B buyers don't have standing mandates with every vendor; requesting payment via a link, not silently debiting, matches how B2B collections actually works and avoids a much larger safety surface.
14. **"What would you build next if hired?"** — A risk-score feedback loop where promise-kept history retroactively adjusts the buyer risk tier, and a merchant-configurable tone/policy editor.
15. **"How is this different from a generic dunning SaaS like an Indian Chaser/Upflow?"** — Those are US/B2B-SaaS-flavored and email-first; none are WhatsApp-first, promise-extraction-native, or built on Razorpay's own invoicing/payment-link rails.
16. **"What's your confidence threshold and how did you pick it?"** — Tuned on the 70% dev split by checking the false-promise rate at each threshold; reported transparently, not hidden.
17. **"Why Postgres and not a vector DB?"** — This isn't a retrieval problem — it's structured state tracking; a vector DB would be complexity with no payoff.
18. **"What's the weakest part of your system?"** — Reply-parsing on truly ambiguous, code-mixed (Hindi/English) replies — acknowledged directly, with the abstention path as the mitigation, not a hidden weakness.
19. **"How would this make money as a Razorpay product?"** — Take-rate-adjacent: faster receivables collection directly improves the merchant's cash position, a natural upsell alongside Razorpay Capital (working-capital lending) — collect faster, borrow less.
20. **"If a judge triggers your live failure case and it doesn't fail gracefully, what then?"** — It's a hand-picked, reproducible test case specifically chosen because we've verified the abstention path handles it — this is exactly why the demo includes it live rather than only in a slide.

---

## PART P — Failure Attack (10 ways this could go wrong, and mitigations)

1. **WhatsApp Business API sandbox access is hard to get in time** → mitigation: build a simulated "inbox" UI that behaves identically; disclose clearly in the pitch that it's simulated for demo purposes, real integration point is documented.
2. **Reply-parsing misclassifies live, unscripted judge input** → mitigation: for the live demo, use the pre-verified failure case (Part J); for anything else, show the confidence-threshold fallback explicitly rather than pretending it's perfect.
3. **Synthetic data looks too clean / cherry-picked** → mitigation: publish the full generation script and the held-out set in the repo; report the three-way baseline comparison, not just DueBot's numbers alone.
4. **Judges see this as "just a CRM with an LLM"** → mitigation: lead the pitch with the promise-tracking and abstention mechanics, not the nudge-sending — that's the actual novelty.
5. **Razorpay Invoices/Payment Links test-mode API has quirks or limits not accounted for** → mitigation: build and test the Razorpay integration first, before any UI polish; keep a mocked-API fallback path so the rest of the demo survives an API hiccup.
6. **Running out of time and shipping an undemonstrated audit log** → mitigation: the audit log view is on the "Must Have" list precisely because it's cheap to build (just render the table) and disproportionately important to the pitch.
7. **Panel asks an architecture question you can't answer under pressure** → mitigation: rehearse Part O's 20 questions specifically; know *why* each component was chosen, especially "why deterministic here, why LLM there."
8. **Repo looks unprofessional (no README, messy commits)** → mitigation: per the buildathon's own advice, treat the README and commit hygiene as a deliverable, not an afterthought.
9. **5-minute pitch runs over or buries the number** → mitigation: script and time it against Part J exactly; the ₹-at-risk number must land in the first 30 seconds.
10. **Team spends the hackathon on the LLM prompt instead of the state machine and safety rails** → mitigation: build the deterministic skeleton (aging, risk tiers, contact caps, audit log) first — it's what makes the project defensible even if the LLM parts are rough on the day.

---

# MY BET

**Build: DueBot — an AI collections agent for overdue B2B receivables, built on Razorpay's Invoices and Payment Links APIs**

**Track: 03 — AI Revenue Recovery**

**One sentence pitch:** DueBot chases overdue B2B invoices on WhatsApp, tracks what buyers actually promise, and escalates the instant a promise breaks — every action bounded, logged, and reversible, in the one corner of merchant revenue recovery Razorpay hasn't shipped into yet.

**Why it wins:** It is the only concept in this research with **zero overlap** against Razorpay's already-shipped Agent Studio (Dispute Responder, Subscription Recovery, Abandoned Cart, RTO Shield/Insights, Cashflow Forecaster, Intelligent Reconciliation all cover B2C/D2C failure-recovery and reconciliation — none touch B2B receivables). It matches Track 03's exact required loop (detect → diagnose → intervene → recover, with stopping rules and an audit trail) natively rather than by force-fitting. It's provably measurable on synthetic data with a real three-way baseline comparison. And it targets Razorpay's actual dominant merchant base — SMEs — not the glossy D2C use case every other builder will reach for first.

**The single most important metric:** ₹ recovered vs. the naive fixed-cadence-reminder baseline, on the same held-out 60-invoice batch — because it isolates what the *agent* actually contributed, not just what a checklist would have recovered anyway.

**The demo moment judges will remember:** the live-triggered ambiguous buyer reply where DueBot correctly refuses to log a promise it isn't confident about, explains why, and hands it to a human — proving in five seconds, without a slide, that this system knows the difference between acting and guessing.
