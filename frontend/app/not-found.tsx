import Link from "next/link";

export default function NotFound() {
  return (
    <div className="mx-auto flex min-h-[60vh] max-w-lg flex-col items-center justify-center text-center">
      <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-2xl border border-sky-500/30 bg-sky-950/40 text-sky-400 shadow-xl shadow-sky-950/50">
        <svg className="h-8 w-8" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      </div>
      <span className="rounded-full border border-sky-500/20 bg-sky-500/10 px-3 py-1 font-mono text-xs font-bold uppercase tracking-wider text-sky-400">
        404 — Not Found
      </span>
      <h1 className="mt-4 text-3xl font-extrabold tracking-tight text-white">Resource Not Found</h1>
      <p className="mt-2 text-sm text-slate-400">
        The requested invoice, buyer profile, or audit log entry could not be located in the database.
      </p>
      <div className="mt-6">
        <Link
          href="/"
          className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-sky-500 to-blue-600 px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-sky-500/20 transition-all hover:scale-105"
        >
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
          </svg>
          Return to Dashboard
        </Link>
      </div>
    </div>
  );
}
