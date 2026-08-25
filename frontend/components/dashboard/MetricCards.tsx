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
        border: "hover:border-amber-400/50",
        glow: "from-amber-500/20 via-orange-500/10 to-transparent",
        iconBg: "bg-amber-500/15 text-amber-300 border-amber-400/30 shadow-lg shadow-amber-500/20",
        path: "M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z",
      };
    }
    if (type === "overdue" || label.includes("Overdue")) {
      return {
        border: "hover:border-rose-400/50",
        glow: "from-rose-500/20 via-pink-500/10 to-transparent",
        iconBg: "bg-rose-500/15 text-rose-300 border-rose-400/30 shadow-lg shadow-rose-500/20",
        path: "M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z",
      };
    }
    return {
      border: "hover:border-sky-400/50",
      glow: "from-sky-500/20 via-blue-500/10 to-transparent",
      iconBg: "bg-sky-500/15 text-sky-300 border-sky-400/30 shadow-lg shadow-sky-500/20",
      path: "M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z",
    };
  };

  const accent = getAccent();

  return (
    <div className={`glass-card group relative overflow-hidden rounded-3xl p-6 transition-all duration-300 ${accent.border} hover:-translate-y-1.5`}>
      <div className={`absolute -top-12 -right-12 h-36 w-36 rounded-full bg-gradient-to-bl ${accent.glow} blur-2xl transition-opacity duration-300 opacity-70 group-hover:opacity-100`} />
      
      <div className="relative z-10 flex items-start justify-between">
        <div>
          <p className="text-[11px] font-bold uppercase tracking-wider text-slate-400">{label}</p>
          <h3 className="mt-3 text-3xl font-extrabold tracking-tight text-white">{value}</h3>
        </div>
        <div className={`flex h-12 w-12 items-center justify-center rounded-2xl border ${accent.iconBg} transition-transform duration-300 group-hover:scale-110`}>
          <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={accent.path} />
          </svg>
        </div>
      </div>

      <div className="relative z-10 mt-5 flex items-center justify-between border-t border-white/[0.06] pt-3">
        {hint ? <p className="text-xs font-medium text-slate-400">{hint}</p> : null}
        {trend ? (
          <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 px-2.5 py-0.5 text-[11px] font-bold text-emerald-300 border border-emerald-400/20 shadow-sm shadow-emerald-500/10">
            ↑ {trend}
          </span>
        ) : null}
      </div>
    </div>
  );
}

export default MetricCard;
