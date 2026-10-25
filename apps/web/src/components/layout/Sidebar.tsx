"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_ITEMS = [
  { href: "/", label: "Dashboard" },
  { href: "/animals", label: "Animals" },
  { href: "/videos", label: "Videos" },
  { href: "/observations", label: "Observations" },
  { href: "/analytics", label: "Analytics" },
  { href: "/monitoring", label: "Monitoring" },
  { href: "/journal", label: "Journal" },
] as const;

/**
 * A React component is a reusable UI function that returns JSX (markup).
 * Sidebar is a client component ("use client") because it needs the current
 * URL path from the browser via usePathname().
 */
export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex w-full flex-col border-b border-border bg-surface/90 px-4 py-5 md:min-h-screen md:w-60 md:border-b-0 md:border-r md:px-5 md:py-8">
      <div className="mb-6 md:mb-10">
        <p className="font-display text-2xl tracking-tight text-sage-900">
          ZooLog AI
        </p>
        <p className="mt-1 text-xs leading-5 text-muted">
          Camera observation journals
        </p>
      </div>

      <nav aria-label="Main" className="flex gap-1 overflow-x-auto md:flex-col md:gap-1.5">
        {NAV_ITEMS.map((item) => {
          const active =
            item.href === "/"
              ? pathname === "/"
              : pathname.startsWith(item.href);

          return (
            <Link
              key={item.href}
              href={item.href}
              className={`whitespace-nowrap rounded-xl px-3 py-2.5 text-sm font-medium transition ${
                active
                  ? "bg-sage-100 text-sage-900"
                  : "text-muted hover:bg-sage-50 hover:text-sage-900"
              }`}
            >
              {item.label}
            </Link>
          );
        })}
      </nav>

      <p className="mt-auto hidden pt-10 text-xs leading-5 text-muted md:block">
        Step 10 — authorized camera monitoring
      </p>
    </aside>
  );
}
