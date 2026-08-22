import "./globals.css";
import type { ReactNode } from "react";
import { Nav } from "../components/ui/Nav";

export const metadata = {
  title: "DueBot",
  description: "AI collections agent for overdue B2B receivables",
};

interface RootLayoutProps {
  children: ReactNode;
}

export default function RootLayout({ children }: RootLayoutProps) {
  return (
    <html lang="en">
      <body>
        <Nav />
        <main className="mx-auto max-w-7xl px-6 py-8">{children}</main>
      </body>
    </html>
  );
}
