interface EdgeCaseMeta {
  label: string;
  className: string;
  title: string;
}

/**
 * The adversarial scenarios the data generator plants in every batch.
 * Each `title` states which policy guardrail that scenario exercises, so a
 * reviewer can hover any badge and see what the invoice is there to prove.
 */
const EDGE_CASE_META: Record<string, EdgeCaseMeta> = {
  partial_payment: {
    label: "Partial Payment",
    className: "border-amber-500/30 bg-amber-500/10 text-amber-300",
    title:
      "Buyer paid part of the invoice. DueBot must chase only the remaining balance, never the full amount.",
  },
  promise_then_silent: {
    label: "Promise -> Silent",
    className: "border-orange-500/30 bg-orange-500/10 text-orange-300",
    title:
      "Buyer promised a date then went unresponsive. Tests broken-promise detection after the grace window.",
  },
  paid_during_nudge_sequence: {
    label: "Paid Mid-Sequence",
    className: "border-emerald-500/30 bg-emerald-500/10 text-emerald-300",
    title:
      "Payment landed while nudges were queued. Tests that the sequence stops immediately on settlement.",
  },
  duplicate_invoice: {
    label: "Duplicate",
    className: "border-slate-500/30 bg-slate-500/10 text-slate-300",
    title: "Same invoice raised twice. Tests deduplication before any contact is sent.",
  },
  disputed_invoice: {
    label: "Disputed",
    className: "border-rose-500/30 bg-rose-500/10 text-rose-300",
    title:
      "Buyer disputes the invoice. The policy gate must block every nudge and route to human review.",
  },
  ambiguous_reply: {
    label: "Ambiguous Reply",
    className: "border-violet-500/30 bg-violet-500/10 text-violet-300",
    title:
      "Reply has no clear intent. The parser must abstain below 70% confidence rather than log a promise.",
  },
  opt_out_mid_sequence: {
    label: "Opted Out",
    className: "border-fuchsia-500/30 bg-fuchsia-500/10 text-fuchsia-300",
    title: "Buyer opted out mid-sequence. All further contact must stop permanently.",
  },
};

export function edgeCaseMeta(edgeCase: string): EdgeCaseMeta {
  return (
    EDGE_CASE_META[edgeCase] ?? {
      label: edgeCase.replace(/_/g, " "),
      className: "border-slate-500/30 bg-slate-500/10 text-slate-300",
      title: edgeCase,
    }
  );
}

interface EdgeCaseBadgeProps {
  edgeCase: string;
}

export function EdgeCaseBadge({ edgeCase }: EdgeCaseBadgeProps) {
  if (!edgeCase || edgeCase === "none") return null;
  const meta = edgeCaseMeta(edgeCase);
  return (
    <span
      title={meta.title}
      className={`inline-flex cursor-help rounded border px-1.5 py-0.5 text-[9px] font-extrabold uppercase tracking-wide ${meta.className}`}
    >
      {meta.label}
    </span>
  );
}

export default EdgeCaseBadge;
