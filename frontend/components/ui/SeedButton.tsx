"use client";

import { useState } from "react";
import { seedDemo } from "../../lib/api";

interface SeedButtonProps {
  label?: string;
}

export function SeedButton({ label = "Seed synthetic batch" }: SeedButtonProps) {
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  return (
    <div>
      <button
        type="button"
        disabled={busy}
        className="rounded-md bg-sky-500 px-4 py-2 text-sm font-medium text-ink disabled:opacity-50"
        onClick={() => {
          setBusy(true);
          void seedDemo()
            .then((result) => {
              setMessage(`Seeded ${result.data.invoices} invoices`);
              window.location.reload();
            })
            .catch((err: unknown) => {
              setMessage(err instanceof Error ? err.message : "Seed failed");
              setBusy(false);
            });
        }}
      >
        {label}
      </button>
      {message ? <p className="mt-2 text-sm text-slate-400">{message}</p> : null}
    </div>
  );
}
