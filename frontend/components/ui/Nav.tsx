"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { checkHealth } from "../../lib/api";

const LINKS = [
  { href: "/", label: "Overview" },
  { href: "/invoices", label: "Invoices" },
  { href: "/buyers", label: "Buyers" },
  { href: "/inbox", label: "Inbox & Review" },
  { href: "/audit", label: "Audit Log" },
  { href: "/metrics", label: "Metrics & Baselines" },
];

export function Nav() {
  const pathname = usePathname();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [isHealthy, setIsHealthy] = useState<boolean | null>(null);

  useEffect(() => {
    let isMounted = true;
    const verify = () => {
      checkHealth()
        .then(() => {
          if (isMounted) setIsHealthy(true);
        })
        .catch(() => {
          if (isMounted) setIsHealthy(false);
        });
    };

    verify();
    const interval = setInterval(verify, 10000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  return (
    <header className="sticky top-0 z-40 border-b border-white/[0.08] bg-[#050811]/75 backdrop-blur-2xl transition-all">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3.5 sm:px-6">
        <div className="flex items-center gap-4">
          <Link href="/" className="group flex items-center gap-2.5" aria-label="DueBot Home">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-sky-400 via-blue-500 to-indigo-600 shadow-lg shadow-sky-500/25 transition-transform duration-200 group-hover:scale-105">
              <svg className="h-5 w-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-base font-extrabold tracking-tight text-white group-hover:text-sky-400 transition-colors">DueBot</span>
                <span className="rounded-full bg-gradient-to-r from-sky-500/10 to-blue-500/10 px-2.5 py-0.5 text-[10px] font-extrabold tracking-wider text-sky-400 border border-sky-400/20 shadow-sm shadow-sky-500/10">
                  RAZORPAY AI
                </span>
              </div>
            </div>
          </Link>
        </div>

        {/* Desktop Navigation */}
        <nav className="hidden lg:flex items-center gap-1 rounded-2xl border border-white/[0.08] bg-slate-900/60 p-1.5 text-sm backdrop-blur-xl shadow-inner" aria-label="Main Navigation">
          {LINKS.map((link) => {
            const isActive = pathname === link.href || (link.href !== "/" && pathname.startsWith(link.href));
            return (
              <Link
                key={link.href}
                href={link.href}
                aria-current={isActive ? "page" : undefined}
                className={`relative rounded-xl px-3.5 py-1.5 text-xs font-bold transition-all duration-200 ${
                  isActive
                    ? "bg-gradient-to-r from-sky-500 to-blue-600 text-white shadow-lg shadow-sky-500/25"
                    : "text-slate-400 hover:bg-white/[0.05] hover:text-slate-200"
                }`}
              >
                {link.label}
              </Link>
            );
          })}
        </nav>

        <div className="flex items-center gap-3">
          <div
            className={`hidden sm:flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-medium transition-all ${
              isHealthy === true
                ? "border-emerald-500/30 bg-emerald-950/40 text-emerald-400"
                : isHealthy === false
                  ? "border-amber-500/30 bg-amber-950/40 text-amber-300"
                  : "border-slate-700 bg-slate-800/40 text-slate-400"
            }`}
          >
            <span className="relative flex h-2 w-2">
              <span
                className={`absolute inline-flex h-full w-full rounded-full opacity-75 ${
                  isHealthy === true
                    ? "bg-emerald-400 animate-ping"
                    : isHealthy === false
                      ? "bg-amber-400 animate-ping"
                      : "bg-slate-400"
                }`}
              />
              <span
                className={`relative inline-flex h-2 w-2 rounded-full ${
                  isHealthy === true
                    ? "bg-emerald-500"
                    : isHealthy === false
                      ? "bg-amber-500"
                      : "bg-slate-500"
                }`}
              />
            </span>
            <span>
              {isHealthy === true
                ? "Policy Engine Active"
                : isHealthy === false
                  ? "Backend Offline"
                  : "Connecting..."}
            </span>
          </div>

          {/* Mobile Hamburger Button */}
          <button
            type="button"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="flex h-9 w-9 items-center justify-center rounded-xl border border-slate-800 bg-panel/80 text-slate-300 transition-colors hover:bg-slate-800 lg:hidden"
            aria-label={mobileMenuOpen ? "Close navigation menu" : "Open navigation menu"}
            aria-expanded={mobileMenuOpen}
            aria-controls="mobile-nav-menu"
          >
            {mobileMenuOpen ? (
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            ) : (
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            )}
          </button>
        </div>
      </div>

      {/* Mobile Drawer Menu */}
      {mobileMenuOpen && (
        <nav
          id="mobile-nav-menu"
          className="border-t border-slate-800/80 bg-ink/95 px-4 py-3 lg:hidden"
          aria-label="Mobile Navigation"
        >
          <div className="grid grid-cols-2 gap-2">
            {LINKS.map((link) => {
              const isActive = pathname === link.href || (link.href !== "/" && pathname.startsWith(link.href));
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  onClick={() => setMobileMenuOpen(false)}
                  aria-current={isActive ? "page" : undefined}
                  className={`rounded-xl px-3 py-2 text-xs font-semibold transition-all ${
                    isActive
                      ? "bg-gradient-to-r from-sky-500 to-blue-600 text-white shadow-md shadow-sky-500/20"
                      : "border border-slate-800/60 bg-panel/40 text-slate-300 hover:bg-slate-800/60 hover:text-white"
                  }`}
                >
                  {link.label}
                </Link>
              );
            })}
          </div>
        </nav>
      )}
    </header>
  );
}

export default Nav;
