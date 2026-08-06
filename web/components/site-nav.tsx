"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Logo } from "@/components/logo";

// Top navigation, ordered by how often the daily loop needs each page.
const links = [
  { href: "/", label: "Home" },
  { href: "/today", label: "Apply today" },
  { href: "/manual-jd", label: "Paste JD" },
  { href: "/jobs", label: "Jobs" },
  { href: "/kb", label: "Knowledge Base" },
  { href: "/profile", label: "Profile" },
  { href: "/templates", label: "Templates" },
  { href: "/settings", label: "Filters" },
  // Last: the list is ordered by how often the daily loop needs a page, and the
  // wall is needed never.
  { href: "/board", label: "Board" },
];

export function SiteNav() {
  const pathname = usePathname();
  const [waiting, setWaiting] = useState<number | null>(null);

  // The count on "Apply today" answers "is there work?" without a click. It is
  // re-read on navigation because applying to something changes it.
  useEffect(() => {
    api
      .setupStatus()
      .then((s) => setWaiting(s.counts.rankable))
      .catch(() => setWaiting(null));
  }, [pathname]);

  return (
    <header className="border-b">
      <nav className="max-w-5xl mx-auto px-6 min-h-14 py-2 flex items-center gap-x-6 gap-y-1 flex-wrap">
        <Link
          href="/"
          className="rounded-sm focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50"
        >
          <Logo />
        </Link>
        <div className="flex items-center gap-x-4 gap-y-1 text-sm text-muted-foreground flex-wrap">
          {links.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              aria-current={pathname === l.href ? "page" : undefined}
              className={`rounded-sm hover:text-foreground focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50 ${
                pathname === l.href ? "text-foreground font-medium" : ""
              }`}
            >
              {l.label}
              {l.href === "/today" && waiting !== null && waiting > 0 && (
                <span className="tabular-nums"> ({waiting})</span>
              )}
            </Link>
          ))}
        </div>
      </nav>
    </header>
  );
}
