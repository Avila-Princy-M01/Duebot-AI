export default function Loading() {
  return (
    <div className="space-y-6 animate-pulse" aria-busy="true" aria-label="Loading page content">
      <div className="flex items-center justify-between">
        <div className="space-y-2">
          <div className="h-8 w-64 rounded-xl bg-slate-800/80" />
          <div className="h-4 w-96 rounded-lg bg-slate-800/50" />
        </div>
        <div className="flex gap-2">
          <div className="h-9 w-32 rounded-xl bg-slate-800/80" />
          <div className="h-9 w-32 rounded-xl bg-slate-800/80" />
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="h-32 rounded-2xl border border-slate-800/80 bg-panel/40 p-6">
            <div className="h-4 w-24 rounded bg-slate-800" />
            <div className="mt-4 h-8 w-36 rounded-lg bg-slate-800" />
          </div>
        ))}
      </div>

      <div className="h-96 rounded-2xl border border-slate-800/80 bg-panel/40 p-6">
        <div className="h-6 w-48 rounded bg-slate-800 mb-6" />
        <div className="space-y-3">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="h-10 w-full rounded-lg bg-slate-800/50" />
          ))}
        </div>
      </div>
    </div>
  );
}
