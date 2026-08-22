interface NavProps {}

const LINKS = [
  { href: "/", label: "Overview" },
  { href: "/invoices", label: "Invoices" },
  { href: "/buyers", label: "Buyers" },
  { href: "/audit", label: "Audit log" },
  { href: "/metrics", label: "Metrics" },
  { href: "/inbox", label: "Inbox" },
];

export function Nav(_props: NavProps) {
  return (
    <header className="border-b border-slate-800 bg-panel">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
        <a href="/" className="text-lg font-semibold tracking-tight">
          DueBot
        </a>
        <nav className="flex gap-4 text-sm text-slate-300">
          {LINKS.map((link) => (
            <a key={link.href} href={link.href} className="hover:text-white">
              {link.label}
            </a>
          ))}
        </nav>
      </div>
    </header>
  );
}
