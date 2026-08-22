interface MetricCardProps {
  label: string;
  value: string;
  hint?: string;
  trend?: string;
  type?: "loaded" | "overdue" | "risk";
}

export function MetricCard({ label, value, hint, trend, type }: MetricCardProps) {
  const getAccent = () => {
    if (type === "risk" || label.includes("risk")) {
      return {
        border: "hover:border-amber-500/40",
        glow: "from-amber-500/10 to-transparent",
        iconBg: "bg-amber-500/10 text-amber-400 border-amber-500/20",
        path: "M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z",
      };
    }
    if (type === "overdue" || label.includes("Overdue")) {
      return {
        border: "hover:border-rose-500/40",
        glow: "from-rose-500/10 to-transparent",
        iconBg: "bg-rose-500/10 text-rose-400 border-rose-500/20",
        path: "M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z",
      };
    }
    return {
      border: "hover:border-sky-500/40",
      glow: "from-sky-500/10 to-transparent",
      iconBg: "bg-sky-500/10 text-sky-400 border-sky-500/20",
      path: "M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z",
    };
  };

  const accent = getAccent();

  return (
    <div className={`group relative overflow-hidden rounded-2xl border border-slate-800/80 bg-panel/70 p-6 backdrop-blur-md transition-all duration-300 ${accent.border} hover:-translate-y-1 hover:shadow-xl shadow-black/40`}>
      <div className={`absolute top-0 right-0 h-28 w-28 bg-gradient-to-bl ${accent.glow} blur-2xl transition-opacity duration-300 opacity-60 group-hover:opacity-100`} />
      
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-bold uppercase tracking-wider text-slate-400">{label}</p>
          <h3 className="mt-3 text-3xl font-extrabold tracking-tight text-white">{value}</h3>
        </div>
        <div className={`flex h-11 w-11 items-center justify-center rounded-xl border ${accent.iconBg}`}>
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={accent.path} />
          </svg>
        </div>
      </div>

      <div className="mt-4 flex items-center justify-between">
        {hint ? <p className="text-xs font-medium text-slate-400">{hint}</p> : null}
        {trend ? (
          <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 px-2 py-0.5 text-[11px] font-bold text-emerald-400 border border-emerald-500/20">
            ↑ {trend}
          </span>
        ) : null}
      </div>
    </div>
  );
}

export default MetricCard;
