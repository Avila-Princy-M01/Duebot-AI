"""
generator.py — Synthetic B2B invoice dataset generator for DueBot.

Produces a realistic, reproducible dataset of Indian SME B2B receivables:
merchants, buyers (with payment-reliability profiles), invoices (with GST,
aging, and lifecycle status), and buyer-reply message threads used to train
and evaluate DueBot's promise-extraction and abstention logic.

Design follows PART M of the strategy doc:
  - 3-5 synthetic SME merchants (services / wholesale / manufacturing / retail-b2b)
  - 40-60 buyers per merchant, split 70% reliable / 20% occasional-late / 10% chronic-late
  - 200+ invoices, amounts log-distributed 5k-5L INR, aging spread 1-90+ days overdue
  - Ground-truth labels: would-have-paid-without-intervention, promise outcome
  - Explicitly injected edge cases: ambiguous replies, mid-sequence opt-out,
    duplicate invoices, partial payments, paid-during-nudge-sequence,
    promise-then-silent, disputed invoices
  - 70/30 train/test split, held out for reported eval numbers

Usage:
    python generator.py
    python generator.py --num-invoices 300 --seed 7 --output-dir ./output
    python generator.py --format json

Output (CSV by default, one file per table):
    merchants.csv
    buyers.csv
    invoices.csv
    messages.csv
    manifest.json   (run metadata + summary stats, always written)
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
import uuid
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, cast

from faker import Faker

# ---------------------------------------------------------------------------
# Simulation constants
# ---------------------------------------------------------------------------

# "Today" for the simulation. Invoice aging, statuses, and message timestamps
# are all computed relative to this fixed reference date so the dataset is
# reproducible regardless of when the script is actually run.
SIM_TODAY = date(2026, 8, 21)

BUSINESS_TYPES = ["services", "wholesale", "manufacturing", "retail_b2b"]

GST_RATES = [0, 5, 12, 18, 28]
GST_WEIGHTS = [0.05, 0.10, 0.20, 0.55, 0.10]  # 18% is modal for B2B services/goods

PAYMENT_TERMS_DAYS = [15, 30, 45, 60]
PAYMENT_TERMS_WEIGHTS = [0.15, 0.55, 0.20, 0.10]

INDIAN_STATE_CODES = [
    "27",
    "29",
    "33",
    "07",
    "19",
    "24",
    "06",
    "36",
    "09",
    "23",
]  # MH, KA, TN, DL, WB, GJ, HR, TS, UP, MP

# Buyer reliability tiers: distribution + behavior parameters that drive
# invoice status simulation downstream.
RELIABILITY_TIERS: dict[str, dict[str, Any]] = {
    "reliable": {
        "weight": 0.70,
        "on_time_rate": (0.85, 0.98),  # sampled range for on_time_payment_rate
        "p_pay_on_time": 0.58,
        "p_pay_late": 0.28,  # pays, but after due date
        "p_still_open": 0.10,
        "p_dispute": 0.04,  # raised from 0.01 so disputes appear organically
        "late_days_range": (1, 20),
        "self_cure_prob": 0.75,  # would pay anyway, even without a nudge
    },
    "occasional_late": {
        "weight": 0.20,
        "on_time_rate": (0.50, 0.80),
        "p_pay_on_time": 0.20,
        "p_pay_late": 0.42,
        "p_still_open": 0.30,
        "p_dispute": 0.08,  # raised from 0.03
        "late_days_range": (5, 45),
        "self_cure_prob": 0.45,
    },
    "chronic_late": {
        "weight": 0.10,
        "on_time_rate": (0.15, 0.45),
        "p_pay_on_time": 0.05,
        "p_pay_late": 0.33,
        "p_still_open": 0.50,
        "p_dispute": 0.12,  # raised from 0.07
        "late_days_range": (15, 95),
        "self_cure_prob": 0.20,
    },
}

MIN_INVOICE_AMOUNT = 5_000
MAX_INVOICE_AMOUNT = 500_000

# Reply text banks for the promise-tracking / reply-parsing message threads.
# Grouped by the intent DueBot's reply-parser is meant to extract.
PROMISE_REPLIES = [
    "Sure, will pay by Friday.",
    "Payment will go out tomorrow morning, sorry for the delay.",
    "Yes noted, clearing this by {date}.",
    "Paisa {date} tak bhej dunga, thoda cash flow issue tha.",
    "Confirmed, I'll settle the full amount by end of this week.",
    "Will transfer by {date}, please hold off on further reminders till then.",
]
AMBIGUOUS_REPLIES = [
    "Will sort it out soon.",
    "Yeah I'm on it, will see.",
    "Let me check with accounts and get back to you.",
    "Should be fine, don't worry.",
    "Dekhta hoon kya kar sakta hoon.",
    "It's in process.",
]
DISPUTE_REPLIES = [
    "This amount is wrong, we already paid half of this via NEFT last month.",
    "We never received the full order, please recheck before asking for payment.",
    "There's a pricing mismatch versus our PO, raising this with your sales team.",
    "This invoice appears to be a duplicate of INV already settled.",
]
OPT_OUT_REPLIES = [
    "Please stop messaging me on this number, contact our accounts email instead.",
    "Do not send further WhatsApp reminders, this is not the right channel.",
    "Kindly remove this number from your reminder list.",
]
OBJECTION_REPLIES = [
    "We're waiting on our own receivables to clear first, can we get 2 more weeks?",
    "Can you resend the invoice with the correct GSTIN? Will process after that.",
    "Our finance team processes payments only on the last working day of the month.",
]

NUDGE_TEMPLATES = [
    "Hi {buyer}, this is a reminder that invoice {invoice_number} for INR {amount} "
    "was due on {due_date}. Could you share an update on payment?",
    "Hi {buyer}, following up on invoice {invoice_number} (INR {amount}), now "
    "{days_overdue} days overdue. Please let us know when we can expect payment.",
    "Hi {buyer}, invoice {invoice_number} for INR {amount} is still outstanding. "
    "Here is the payment link for your convenience: {payment_link}",
]


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class Merchant:
    merchant_id: str
    business_name: str
    business_type: str
    gstin: str
    city: str
    state_code: str
    onboarded_date: str


@dataclass
class Buyer:
    buyer_id: str
    merchant_id: str
    company_name: str
    contact_name: str
    phone: str
    email: str
    gstin: str
    reliability_tier: str
    on_time_payment_rate: float
    relationship_since: str


@dataclass
class Invoice:
    invoice_id: str
    merchant_id: str
    buyer_id: str
    invoice_number: str
    issue_date: str
    due_date: str
    payment_terms_days: int
    subtotal_amount: float
    gst_rate: int
    gst_amount: float
    total_amount: float
    currency: str
    status: str  # paid | partial | pending | overdue | disputed
    amount_paid: float
    paid_date: str | None
    days_overdue: int  # 0 if not overdue as of SIM_TODAY
    risk_tier: str  # low | medium | high
    payment_link_id: str
    edge_case: str  # none | <edge case tag>
    would_have_paid_without_intervention: bool | None
    promise_outcome: str  # none | pending | kept | broken
    split: str  # train | test
    notes: str = ""


@dataclass
class BuyerMessage:
    message_id: str
    invoice_id: str
    buyer_id: str
    channel: str  # whatsapp | email
    direction: str  # outbound | inbound
    timestamp: str
    message_text: str
    intent_label: str  # nudge | promise | ambiguous | dispute | opt_out | objection | silence
    promised_date: str | None = None


# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------


class DueBotDataGenerator:
    def __init__(self, seed: int = 42, locale: str = "en_IN"):
        self.seed = seed
        self.rng = random.Random(seed)
        self.fake = Faker(locale)
        Faker.seed(seed)

        self.merchants: list[Merchant] = []
        self.buyers: list[Buyer] = []
        self.invoices: list[Invoice] = []
        self.messages: list[BuyerMessage] = []

        self._invoice_counter = 0

    # -- helpers ------------------------------------------------------

    def _gstin(self, state_code: str) -> str:
        """Loosely-shaped synthetic GSTIN: not a real checksum, just realistic form."""
        pan_like = "".join(self.rng.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=5))
        pan_like += "".join(self.rng.choices("0123456789", k=4))
        pan_like += self.rng.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
        entity_code = self.rng.choice("123456789")
        return f"{state_code}{pan_like}{entity_code}Z{self.rng.choice('0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ')}"

    def _log_distributed_amount(self) -> float:
        """Log-uniform amount between MIN_INVOICE_AMOUNT and MAX_INVOICE_AMOUNT,
        rounded to a realistic invoice-looking value."""
        low, high = math.log(MIN_INVOICE_AMOUNT), math.log(MAX_INVOICE_AMOUNT)
        amount = math.exp(self.rng.uniform(low, high))
        # round to nearest 100 for amounts under 1L, nearest 1000 above, for realism
        step = 1000 if amount >= 100_000 else 100
        return round(amount / step) * step

    def _next_invoice_number(self, merchant_short: str, issue_date: date) -> str:
        self._invoice_counter += 1
        return f"{merchant_short}/{issue_date.year}/{self._invoice_counter:05d}"

    def _risk_tier(self, tier: str, days_overdue: int) -> str:
        if days_overdue <= 0:
            return "low"
        if tier == "chronic_late" or days_overdue > 60:
            return "high"
        if tier == "occasional_late" or days_overdue > 21:
            return "medium"
        return "low"

    # -- merchants ------------------------------------------------------

    def generate_merchants(self, n: int = 4) -> list[Merchant]:
        n = max(3, min(5, n))
        used_types = (
            self.rng.sample(BUSINESS_TYPES, k=n)
            if n <= len(BUSINESS_TYPES)
            else [self.rng.choice(BUSINESS_TYPES) for _ in range(n)]
        )
        for i in range(n):
            state_code = self.rng.choice(INDIAN_STATE_CODES)
            business_type = used_types[i]
            name_suffix = {
                "services": self.rng.choice(
                    ["Consulting", "Solutions", "Services", "Technologies"]
                ),
                "wholesale": self.rng.choice(
                    ["Trading Co", "Wholesale Traders", "Distributors", "Traders"]
                ),
                "manufacturing": self.rng.choice(
                    ["Industries", "Manufacturing", "Engineering Works", "Fabricators"]
                ),
                "retail_b2b": self.rng.choice(
                    ["Supplies", "Retail Ventures", "Stores", "Enterprises"]
                ),
            }[business_type]
            business_name = f"{self.fake.last_name()} {name_suffix}"
            merchant = Merchant(
                merchant_id=f"MER-{i + 1:03d}",
                business_name=business_name,
                business_type=business_type,
                gstin=self._gstin(state_code),
                city=self.fake.city(),
                state_code=state_code,
                onboarded_date=(SIM_TODAY - timedelta(days=self.rng.randint(180, 900))).isoformat(),
            )
            self.merchants.append(merchant)
        return self.merchants

    # -- buyers ------------------------------------------------------

    def _sample_tier(self) -> str:
        tiers = list(RELIABILITY_TIERS.keys())
        weights: list[float] = [float(RELIABILITY_TIERS[t]["weight"]) for t in tiers]
        return self.rng.choices(tiers, weights=weights, k=1)[0]

    def generate_buyers(self, per_merchant_range: tuple[int, int] = (40, 60)) -> list[Buyer]:
        for merchant in self.merchants:
            n_buyers = self.rng.randint(*per_merchant_range)
            for j in range(n_buyers):
                tier = self._sample_tier()
                rate_range = cast(tuple[float, float], RELIABILITY_TIERS[tier]["on_time_rate"])
                low, high = rate_range[0], rate_range[1]
                phone = self.fake.numerify("+91##########")
                buyer = Buyer(
                    buyer_id=f"{merchant.merchant_id}-BUY-{j + 1:04d}",
                    merchant_id=merchant.merchant_id,
                    company_name=self.fake.company(),
                    contact_name=self.fake.name(),
                    phone=phone,
                    email=self.fake.company_email(),
                    gstin=self._gstin(self.rng.choice(INDIAN_STATE_CODES)),
                    reliability_tier=tier,
                    on_time_payment_rate=round(self.rng.uniform(low, high), 3),
                    relationship_since=(
                        SIM_TODAY - timedelta(days=self.rng.randint(30, 800))
                    ).isoformat(),
                )
                self.buyers.append(buyer)
        return self.buyers

    # -- invoices ------------------------------------------------------

    def _simulate_lifecycle(
        self, tier_params: dict[str, Any], issue_date: date, due_date: date
    ) -> dict[str, Any]:
        """Decide status/paid_date/days_overdue/amount_paid-fraction for one invoice
        given its buyer's tier behavior parameters. Returns a dict of fields."""
        outcome = self.rng.choices(
            ["on_time", "late", "open", "dispute"],
            weights=[
                tier_params["p_pay_on_time"],
                tier_params["p_pay_late"],
                tier_params["p_still_open"],
                tier_params["p_dispute"],
            ],
            k=1,
        )[0]

        if outcome == "on_time":
            paid_date = due_date - timedelta(days=self.rng.randint(0, 5))
            paid_date = max(paid_date, issue_date)
            return {
                "status": "paid",
                "paid_date": paid_date,
                "days_overdue": 0,
                "paid_fraction": 1.0,
            }

        if outcome == "late":
            late_lo, late_hi = tier_params["late_days_range"]
            late_days = self.rng.randint(late_lo, late_hi)
            paid_date = due_date + timedelta(days=late_days)
            if paid_date > SIM_TODAY:
                # would pay late, but that date hasn't arrived yet -> still overdue today
                days_overdue = (SIM_TODAY - due_date).days
                return {
                    "status": "overdue" if days_overdue > 0 else "pending",
                    "paid_date": None,
                    "days_overdue": max(days_overdue, 0),
                    "paid_fraction": 0.0,
                }
            return {
                "status": "paid",
                "paid_date": paid_date,
                "days_overdue": 0,
                "paid_fraction": 1.0,
            }

        if outcome == "dispute":
            days_overdue = max((SIM_TODAY - due_date).days, 0)
            return {
                "status": "disputed",
                "paid_date": None,
                "days_overdue": days_overdue,
                "paid_fraction": 0.0,
            }

        # still open / overdue as of SIM_TODAY
        days_overdue = (SIM_TODAY - due_date).days
        return {
            "status": "overdue" if days_overdue > 0 else "pending",
            "paid_date": None,
            "days_overdue": max(days_overdue, 0),
            "paid_fraction": 0.0,
        }

    def generate_invoices(self, count: int = 220) -> list[Invoice]:
        if not self.buyers:
            raise RuntimeError("generate_buyers() must run before generate_invoices()")

        merchant_short = {
            m.merchant_id: m.business_name.split()[0][:4].upper() for m in self.merchants
        }
        buyers_by_merchant: dict[str, list[Buyer]] = {}
        for b in self.buyers:
            buyers_by_merchant.setdefault(b.merchant_id, []).append(b)

        for _ in range(count):
            merchant = self.rng.choice(self.merchants)
            buyer = self.rng.choice(buyers_by_merchant[merchant.merchant_id])
            tier_params = RELIABILITY_TIERS[buyer.reliability_tier]

            terms = self.rng.choices(PAYMENT_TERMS_DAYS, weights=PAYMENT_TERMS_WEIGHTS, k=1)[0]
            # Spread issue dates so that with these terms, aging covers 1-90+ days overdue
            # as well as some not-yet-due / recently-paid invoices for realism.
            days_since_issue = self.rng.randint(1, terms + 90)
            issue_date = SIM_TODAY - timedelta(days=days_since_issue)
            due_date = issue_date + timedelta(days=terms)

            subtotal = self._log_distributed_amount()
            gst_rate = self.rng.choices(GST_RATES, weights=GST_WEIGHTS, k=1)[0]
            gst_amount = round(subtotal * gst_rate / 100, 2)
            total = round(subtotal + gst_amount, 2)

            lifecycle = self._simulate_lifecycle(tier_params, issue_date, due_date)
            status = lifecycle["status"]
            days_overdue = lifecycle["days_overdue"]
            paid_fraction = lifecycle["paid_fraction"]
            paid_date = lifecycle["paid_date"]

            amount_paid = round(total * paid_fraction, 2)

            would_have_paid = None
            promise_outcome = "none"
            if status in ("overdue", "disputed"):
                would_have_paid = self.rng.random() < float(tier_params["self_cure_prob"])
                if status == "overdue":
                    promise_outcome = self.rng.choices(
                        ["none", "pending", "kept", "broken"],
                        weights=[0.35, 0.15, 0.30, 0.20],
                        k=1,
                    )[0]

            invoice = Invoice(
                invoice_id=f"INV-{uuid.uuid4().hex[:10]}",
                merchant_id=merchant.merchant_id,
                buyer_id=buyer.buyer_id,
                invoice_number=self._next_invoice_number(
                    merchant_short[merchant.merchant_id], issue_date
                ),
                issue_date=issue_date.isoformat(),
                due_date=due_date.isoformat(),
                payment_terms_days=terms,
                subtotal_amount=subtotal,
                gst_rate=gst_rate,
                gst_amount=gst_amount,
                total_amount=total,
                currency="INR",
                status=status,
                amount_paid=amount_paid,
                paid_date=paid_date.isoformat() if paid_date else None,
                days_overdue=days_overdue,
                risk_tier=self._risk_tier(buyer.reliability_tier, days_overdue),
                payment_link_id=f"plink_{uuid.uuid4().hex[:14]}",
                edge_case="none",
                would_have_paid_without_intervention=would_have_paid,
                promise_outcome=promise_outcome,
                split=self.rng.choices(["train", "test"], weights=[0.70, 0.30], k=1)[0],
            )
            self.invoices.append(invoice)

        return self.invoices

    # -- edge case injection ------------------------------------------------------

    def inject_edge_cases(
        self,
        n_ambiguous: int = 10,
        n_opt_out: int = 8,
        n_duplicate_pairs: int = 3,
        n_partial: int = 8,
        n_paid_during_sequence: int = 6,
        n_promise_then_silent: int = 10,
        n_disputed: int = 12,
        n_objection: int = 8,
    ) -> None:
        """Explicitly overwrite a subset of generated invoices to guarantee each
        edge case from PART M is present in fixed, known quantities, regardless
        of what the random lifecycle simulation happened to produce. This makes
        the dataset's stress-test coverage deterministic and easy to assert on
        in tests, rather than relying on incidental random occurrence."""

        needed = (
            n_ambiguous
            + n_opt_out
            + n_duplicate_pairs
            + n_partial
            + n_paid_during_sequence
            + n_promise_then_silent
            + n_disputed
            + n_objection
        )
        overdue_pool = [
            inv for inv in self.invoices if inv.status == "overdue" and inv.edge_case == "none"
        ]

        # Safety net: if the random lifecycle simulation didn't produce enough overdue
        # invoices to guarantee every edge-case quota, convert some pending/paid
        # invoices (buyer's true reliability tier doesn't matter for the edge-case
        # itself) into overdue ones so the quotas are always met deterministically.
        if len(overdue_pool) < needed:
            buyers_by_id = {b.buyer_id: b for b in self.buyers}
            candidates = [
                inv
                for inv in self.invoices
                if inv.status in ("pending", "paid") and inv.edge_case == "none"
            ]
            self.rng.shuffle(candidates)
            for inv in candidates:
                if len(overdue_pool) >= needed:
                    break
                due = date.fromisoformat(inv.due_date)
                if due >= SIM_TODAY:
                    # push the due date into the past so it reads as overdue
                    shift = (SIM_TODAY - due).days + self.rng.randint(5, 45)
                    due = due - timedelta(days=-shift) if shift < 0 else due
                    inv.due_date = (due - timedelta(days=self.rng.randint(5, 45))).isoformat()
                    due = date.fromisoformat(inv.due_date)
                inv.status = "overdue"
                inv.amount_paid = 0.0
                inv.paid_date = None
                inv.days_overdue = max((SIM_TODAY - due).days, 1)
                buyer = buyers_by_id[inv.buyer_id]
                inv.risk_tier = self._risk_tier(buyer.reliability_tier, inv.days_overdue)
                overdue_pool.append(inv)

        self.rng.shuffle(overdue_pool)
        pool_iter = iter(overdue_pool)

        def _take(n: int) -> list[Invoice]:
            taken = []
            for _ in range(n):
                try:
                    taken.append(next(pool_iter))
                except StopIteration:
                    break
            return taken

        # 1. Ambiguous reply -> abstention test. Invoice stays overdue, no promise logged.
        for inv in _take(n_ambiguous):
            inv.edge_case = "ambiguous_reply"
            inv.promise_outcome = "none"
            inv.notes = "Buyer reply is ambiguous; DueBot must abstain from logging a promise."

        # 2. Opt-out mid-sequence -> buyer asks to stop being messaged on this channel.
        for inv in _take(n_opt_out):
            inv.edge_case = "opt_out_mid_sequence"
            inv.promise_outcome = "none"
            inv.notes = (
                "Buyer opted out of WhatsApp reminders mid-sequence; must switch channel or stop."
            )

        # 3. Duplicate invoices -> same buyer, same amount, overlapping issue window.
        for inv in _take(n_duplicate_pairs):
            dup = Invoice(**asdict(inv))
            dup.invoice_id = f"INV-{uuid.uuid4().hex[:10]}"
            dup.invoice_number = inv.invoice_number + "-DUP"
            dup.edge_case = "duplicate_invoice"
            dup.notes = f"Likely duplicate of {inv.invoice_id}; same buyer and amount."
            inv.edge_case = "duplicate_invoice"
            inv.notes = f"Has a likely duplicate: see invoices tagged duplicate_invoice for buyer {inv.buyer_id}."
            self.invoices.append(dup)

        # 4. Partial payment -> some amount paid, balance still outstanding and overdue.
        for inv in _take(n_partial):
            inv.status = "partial"
            fraction = self.rng.uniform(0.2, 0.75)
            inv.amount_paid = round(inv.total_amount * fraction, 2)
            inv.paid_date = (
                SIM_TODAY - timedelta(days=self.rng.randint(1, max(inv.days_overdue, 1)))
            ).isoformat()
            inv.edge_case = "partial_payment"
            inv.notes = f"Partially paid ({fraction:.0%}); remaining balance still overdue."

        # 5. Paid during nudge sequence -> must be detected and the sequence stopped.
        for inv in _take(n_paid_during_sequence):
            inv.edge_case = "paid_during_nudge_sequence"
            inv.status = "paid"
            inv.amount_paid = inv.total_amount
            inv.paid_date = (SIM_TODAY - timedelta(days=self.rng.randint(0, 3))).isoformat()
            inv.days_overdue = 0
            inv.promise_outcome = "kept"
            inv.notes = "Paid mid-sequence after 2nd nudge; DueBot must detect payment and halt further nudges."

        # 6. Promise then silent -> buyer commits a date, then stops responding (broken via silence).
        for inv in _take(n_promise_then_silent):
            inv.edge_case = "promise_then_silent"
            inv.promise_outcome = "broken"
            inv.notes = (
                "Buyer promised a payment date, then went unresponsive; promise treated as broken."
            )

        # 7. Disputed invoice -> must not be chased, must be flagged to a human.
        for inv in _take(n_disputed):
            inv.edge_case = "disputed_invoice"
            inv.status = "disputed"
            inv.promise_outcome = "none"
            inv.would_have_paid_without_intervention = False
            inv.notes = (
                "Buyer disputes the invoice; automated chasing must halt and escalate to human."
            )

        # 8. Objection / Extension request -> buyer requests short extension; re-queued into nudge cycle.
        for inv in _take(n_objection):
            inv.edge_case = "objection_extension"
            inv.promise_outcome = "none"
            inv.notes = "Buyer requested short payment extension; re-queued into nudge cycle."

    # -- messages (promise-tracking conversation threads) ------------------------------------------------------

    def generate_messages(self) -> list[BuyerMessage]:
        buyers_by_id = {b.buyer_id: b for b in self.buyers}

        for inv in self.invoices:
            if inv.status not in ("overdue", "partial", "disputed") and inv.edge_case not in (
                "paid_during_nudge_sequence",
            ):
                continue

            buyer = buyers_by_id[inv.buyer_id]
            nudge_delay_days = min(max(inv.days_overdue, 1), 3)
            ts = datetime.fromisoformat(inv.due_date) + timedelta(
                days=nudge_delay_days, hours=self.rng.randint(9, 17)
            )

            # Outbound nudge, always present for any invoice with a thread.
            template = self.rng.choice(NUDGE_TEMPLATES)
            nudge_text = template.format(
                buyer=buyer.contact_name.split()[0],
                invoice_number=inv.invoice_number,
                amount=f"{inv.total_amount:,.0f}",
                due_date=inv.due_date,
                days_overdue=inv.days_overdue,
                payment_link=f"https://rzp.io/l/{inv.payment_link_id[-8:]}",
            )
            self.messages.append(
                BuyerMessage(
                    message_id=f"MSG-{uuid.uuid4().hex[:10]}",
                    invoice_id=inv.invoice_id,
                    buyer_id=buyer.buyer_id,
                    channel="whatsapp",
                    direction="outbound",
                    timestamp=ts.isoformat(),
                    message_text=nudge_text,
                    intent_label="nudge",
                )
            )

            reply_ts = ts + timedelta(hours=self.rng.randint(2, 24))
            sim_now_limit = datetime(2026, 8, 21, 17, 30, 0)
            if reply_ts > sim_now_limit:
                reply_ts = sim_now_limit - timedelta(minutes=self.rng.randint(5, 120))

            if inv.edge_case == "ambiguous_reply":
                self._append_reply(
                    inv, buyer, reply_ts, self.rng.choice(AMBIGUOUS_REPLIES), "ambiguous"
                )

            elif inv.edge_case == "opt_out_mid_sequence":
                self._append_reply(
                    inv, buyer, reply_ts, self.rng.choice(OPT_OUT_REPLIES), "opt_out"
                )

            elif inv.edge_case in ("disputed_invoice",) or inv.status == "disputed":
                self._append_reply(
                    inv, buyer, reply_ts, self.rng.choice(DISPUTE_REPLIES), "dispute"
                )

            elif inv.edge_case == "promise_then_silent":
                due_d = date.fromisoformat(inv.due_date)
                promised = min(
                    due_d + timedelta(days=nudge_delay_days + self.rng.randint(2, 5)),
                    SIM_TODAY - timedelta(days=5),
                )
                text = self.rng.choice(PROMISE_REPLIES).format(date=promised.strftime("%b %d"))
                self._append_reply(
                    inv, buyer, reply_ts, text, "promise", promised_date=promised.isoformat()
                )
                # then silence: no further inbound message, only a follow-up outbound nudge later
                followup_ts = reply_ts + timedelta(days=self.rng.randint(2, 4))
                if followup_ts > sim_now_limit:
                    followup_ts = sim_now_limit - timedelta(minutes=self.rng.randint(1, 30))
                self.messages.append(
                    BuyerMessage(
                        message_id=f"MSG-{uuid.uuid4().hex[:10]}",
                        invoice_id=inv.invoice_id,
                        buyer_id=buyer.buyer_id,
                        channel="whatsapp",
                        direction="outbound",
                        timestamp=followup_ts.isoformat(),
                        message_text=f"Hi {buyer.contact_name.split()[0]}, following up on your promised "
                        f"payment for {inv.invoice_number} - we haven't received it yet or heard back. "
                        f"Could you confirm status?",
                        intent_label="nudge",
                    )
                )

            elif inv.edge_case == "objection_extension":
                self._append_reply(
                    inv, buyer, reply_ts, self.rng.choice(OBJECTION_REPLIES), "objection"
                )

            elif inv.edge_case == "paid_during_nudge_sequence":
                promised = SIM_TODAY - timedelta(days=1)
                text = self.rng.choice(PROMISE_REPLIES).format(date="today")
                self._append_reply(
                    inv, buyer, reply_ts, text, "promise", promised_date=promised.isoformat()
                )

            elif inv.promise_outcome in ("kept", "broken", "pending"):
                if inv.promise_outcome == "broken":
                    due_d = date.fromisoformat(inv.due_date)
                    promised = min(
                        due_d + timedelta(days=nudge_delay_days + self.rng.randint(2, 5)),
                        SIM_TODAY - timedelta(days=5),
                    )
                elif inv.promise_outcome == "kept":
                    promised = SIM_TODAY - timedelta(days=self.rng.randint(1, 10))
                else:
                    promised = SIM_TODAY + timedelta(days=self.rng.randint(1, 7))
                text = self.rng.choice(PROMISE_REPLIES).format(date=promised.strftime("%b %d"))
                self._append_reply(
                    inv, buyer, reply_ts, text, "promise", promised_date=promised.isoformat()
                )

            elif inv.risk_tier in ("medium", "high") and self.rng.random() < 0.35:
                self._append_reply(
                    inv, buyer, reply_ts, self.rng.choice(OBJECTION_REPLIES), "objection"
                )

            # else: no inbound reply at all (silence) - intentionally not synthesized as a
            # message row; absence of an inbound row after a nudge *is* the silence signal.

        return self.messages

    def _append_reply(
        self,
        inv: Invoice,
        buyer: Buyer,
        ts: datetime,
        text: str,
        intent: str,
        promised_date: str | None = None,
    ) -> None:
        self.messages.append(
            BuyerMessage(
                message_id=f"MSG-{uuid.uuid4().hex[:10]}",
                invoice_id=inv.invoice_id,
                buyer_id=buyer.buyer_id,
                channel="whatsapp",
                direction="inbound",
                timestamp=ts.isoformat(),
                message_text=text,
                intent_label=intent,
                promised_date=promised_date,
            )
        )

    # -- orchestration ------------------------------------------------------

    def run(self, num_invoices: int = 260) -> None:
        self.generate_merchants()
        self.generate_buyers()
        self.generate_invoices(count=num_invoices)
        self.inject_edge_cases()
        self.generate_messages()

    def summary(self) -> dict[str, Any]:
        status_counts: dict[str, int] = {}
        edge_case_counts: dict[str, int] = {}
        split_counts: dict[str, int] = {}
        for inv in self.invoices:
            status_counts[inv.status] = status_counts.get(inv.status, 0) + 1
            edge_case_counts[inv.edge_case] = edge_case_counts.get(inv.edge_case, 0) + 1
            split_counts[inv.split] = split_counts.get(inv.split, 0) + 1

        return {
            "seed": self.seed,
            "sim_today": SIM_TODAY.isoformat(),
            "merchants": len(self.merchants),
            "buyers": len(self.buyers),
            "invoices": len(self.invoices),
            "messages": len(self.messages),
            "invoice_status_breakdown": status_counts,
            "invoice_edge_case_breakdown": edge_case_counts,
            "invoice_split_breakdown": split_counts,
            "total_receivables_at_risk_inr": round(
                sum(
                    inv.total_amount - inv.amount_paid
                    for inv in self.invoices
                    if inv.status in ("overdue", "partial", "disputed")
                ),
                2,
            ),
        }

    # -- output ------------------------------------------------------

    def write_csv(self, output_dir: Path) -> None:
        output_dir.mkdir(parents=True, exist_ok=True)
        self._write_table(output_dir / "merchants.csv", self.merchants)
        self._write_table(output_dir / "buyers.csv", self.buyers)
        self._write_table(output_dir / "invoices.csv", self.invoices)
        self._write_table(output_dir / "messages.csv", self.messages)

    @staticmethod
    def _write_table(path: Path, rows: list[Any]) -> None:
        if not rows:
            return
        fieldnames = list(asdict(rows[0]).keys())
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow(asdict(row))

    def write_json(self, output_dir: Path) -> None:
        output_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "merchants": [asdict(m) for m in self.merchants],
            "buyers": [asdict(b) for b in self.buyers],
            "invoices": [asdict(i) for i in self.invoices],
            "messages": [asdict(m) for m in self.messages],
        }
        with open(output_dir / "dataset.json", "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, default=str)

    def write_manifest(self, output_dir: Path) -> None:
        output_dir.mkdir(parents=True, exist_ok=True)
        with open(output_dir / "manifest.json", "w", encoding="utf-8") as f:
            json.dump(self.summary(), f, indent=2)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic B2B invoice data for DueBot.")
    parser.add_argument(
        "--num-invoices",
        type=int,
        default=260,
        help="Base invoice count before edge-case duplicates are added (default: 260)",
    )
    parser.add_argument(
        "--seed", type=int, default=42, help="Random seed for reproducibility (default: 42)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=str(Path(__file__).parent / "output"),
        help="Directory to write output files to",
    )
    parser.add_argument(
        "--format",
        choices=["csv", "json", "both"],
        default="csv",
        help="Output format (default: csv)",
    )
    args = parser.parse_args()

    generator = DueBotDataGenerator(seed=args.seed)
    generator.run(num_invoices=args.num_invoices)

    output_dir = Path(args.output_dir)
    if args.format in ("csv", "both"):
        generator.write_csv(output_dir)
    if args.format in ("json", "both"):
        generator.write_json(output_dir)
    generator.write_manifest(output_dir)

    summary = generator.summary()
    print(
        f"Generated {summary['invoices']} invoices, {summary['buyers']} buyers, "
        f"{summary['merchants']} merchants, {summary['messages']} messages."
    )
    print(f"Total receivables at risk: INR {summary['total_receivables_at_risk_inr']:,.2f}")
    print(f"Status breakdown: {summary['invoice_status_breakdown']}")
    print(f"Edge case breakdown: {summary['invoice_edge_case_breakdown']}")
    print(f"Output written to: {output_dir.resolve()}")


if __name__ == "__main__":
    main()
