"use client";

interface ErrorPageProps {
  error: Error;
  reset: () => void;
}

export function ErrorPage({ error, reset }: ErrorPageProps) {
  return (
    <div className="rounded-xl border border-red-500/40 bg-red-950/40 p-6">
      <h2 className="text-lg font-semibold text-red-200">Something went wrong</h2>
      <p className="mt-2 text-sm text-red-100/80">{error.message}</p>
      <button
        type="button"
        onClick={reset}
        className="mt-4 rounded-md bg-red-500 px-3 py-1.5 text-sm font-medium text-white"
      >
        Retry
      </button>
    </div>
  );
}

export default ErrorPage;
