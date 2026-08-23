"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { seedDemo } from "../../lib/api";

interface SeedButtonProps {
  label?: string;
}

export function SeedButton({ label = "Seed Synthetic Batch" }: SeedButtonProps) {
  const router = useRouter();
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  return (
    <div className="flex flex-col items-start gap-2">
      <button
        type="button"
        disabled={busy}
        className="group relative flex items-center gap-2 overflow-hidden rounded-xl bg-gradient-to-r from-sky-500 via-blue-600 to-indigo-600 px-5 py-2.5 text-xs font-bold text-white shadow-lg shadow-sky-500/25 transition-all duration-200 hover:shadow-sky-500/40 hover:scale-[1.02] active:scale-[0.98] disabled:opacity-50"
        onClick={() => {
          setBusy(true);
          setMessage(null);
          void seedDemo()
            .then((result) => {
              setMessage(`Successfully seeded ${result.data.invoices} invoices & ${result.data.buyers} buyers!`);
              setBusy(false);
              router.refresh();
            })
            .catch((err: unknown) => {
              setMessage(err instanceof Error ? err.message : "Seed failed");
              setBusy(false);
            });
        }}
      >
        {busy ? (
          <svg className="h-4 w-4 animate-spin text-white" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
        ) : (
          <svg className="h-4 w-4 text-white transition-transform group-hover:rotate-180 duration-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
        )}
        <span>{busy ? "Seeding Synthetic Batch..." : label}</span>
      </button>

      {message ? (
        <div className="flex items-center gap-2 rounded-lg border border-emerald-500/30 bg-emerald-950/40 px-3 py-1.5 text-xs text-emerald-300">
          <svg className="h-3.5 w-3.5 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
          <span>{message}</span>
        </div>
      ) : null}
    </div>
  );
}

export default SeedButton;
