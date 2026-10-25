"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { cn } from "@/lib/cn";
import { getToken, getMe, logout, type CurrentUser } from "@/lib/api";
import { Icon } from "@/components/ui/Icon";
import { ThemeToggle } from "@/components/ThemeToggle";
import { UserMenu } from "@/components/UserMenu";

type NavItem = { href: string; label: string; icon: React.ReactNode };

const RESIDENT: NavItem[] = [
  { href: "/submit", label: "Submit", icon: <Icon.clipboard className="h-4.5 w-4.5" /> },
  { href: "/track", label: "Track", icon: <Icon.search className="h-4.5 w-4.5" /> },
];
const STAFF: NavItem[] = [
  { href: "/staff", label: "Dashboard", icon: <Icon.inbox className="h-4.5 w-4.5" /> },
  { href: "/review", label: "AI Review", icon: <Icon.sparkles className="h-4.5 w-4.5" /> },
  { href: "/analytics", label: "Analytics", icon: <Icon.chart className="h-4.5 w-4.5" /> },
];

function Brand() {
  return (
    <Link href="/" className="flex items-center gap-2.5">
      <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-brand-500 to-brand-700 text-white shadow-sm">
        <Icon.pin className="h-5 w-5" />
      </span>
      <span className="flex flex-col leading-none">
        <span className="font-bold tracking-tight text-content">CivicRoute AI</span>
        <span className="text-[11px] text-content-subtle">Civic routing platform</span>
      </span>
    </Link>
  );
}

function NavLinks({
  items,
  pathname,
  onNavigate,
  variant = "desktop",
}: {
  items: NavItem[];
  pathname: string;
  onNavigate?: () => void;
  variant?: "desktop" | "mobile";
}) {
  return (
    <>
      {items.map((item) => {
        const active =
          pathname === item.href || pathname.startsWith(item.href + "/");
        return (
          <Link
            key={item.href}
            href={item.href}
            onClick={onNavigate}
            aria-current={active ? "page" : undefined}
            className={cn(
              "flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
              variant === "mobile" && "w-full",
              active
                ? "bg-brand-50 text-brand-700 dark:bg-brand-500/15 dark:text-brand-300"
                : "text-content-muted hover:bg-surface-muted hover:text-content",
            )}
          >
            {item.icon}
            {item.label}
          </Link>
        );
      })}
    </>
  );
}

function AuthControl({
  onNavigate,
  variant = "desktop",
}: {
  onNavigate?: () => void;
  variant?: "desktop" | "mobile";
}) {
  const router = useRouter();
  const pathname = usePathname();
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [loading, setLoading] = useState(true);

  // Validate the stored session against the backend on mount and on route
  // changes (so a post-login redirect reflects the signed-in state, and an
  // expired session is detected and cleared). Reuses the existing auth client.
  useEffect(() => {
    let cancelled = false;
    if (getToken() == null) {
      setUser(null);
      setLoading(false);
      return;
    }
    setLoading(true);
    getMe()
      .then((u) => {
        if (!cancelled) setUser(u);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [pathname]);

  function signOut() {
    logout(); // securely clears the stored token (existing auth system)
    setUser(null);
    onNavigate?.();
    router.push("/");
    router.refresh();
  }

  if (loading) {
    return (
      <div
        className={cn(
          "flex items-center gap-2",
          variant === "mobile" && "px-3 py-2",
        )}
        aria-busy="true"
      >
        <span className="h-8 w-8 animate-pulse rounded-full bg-surface-muted" />
        <span className="hidden h-4 w-20 animate-pulse rounded bg-surface-muted sm:inline-block" />
      </div>
    );
  }

  if (user) {
    return <UserMenu user={user} onSignOut={signOut} variant={variant} />;
  }

  return (
    <Link
      href="/login"
      onClick={onNavigate}
      className="flex items-center gap-2 rounded-lg bg-brand-600 px-3.5 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-700"
    >
      <Icon.shield className="h-4.5 w-4.5" />
      Staff sign in
    </Link>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);

  // Close the mobile menu whenever the route changes.
  useEffect(() => {
    setMenuOpen(false);
  }, [pathname]);

  return (
    <div className="flex min-h-screen flex-col">
      <header className="sticky top-0 z-40 border-b border-border bg-surface/80 backdrop-blur supports-[backdrop-filter]:bg-surface/70">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between gap-4 px-4 sm:px-6">
          <Brand />

          <nav className="hidden items-center gap-1 lg:flex" aria-label="Primary">
            <NavLinks items={RESIDENT} pathname={pathname} />
            <span className="mx-1 h-5 w-px bg-border" aria-hidden />
            <NavLinks items={STAFF} pathname={pathname} />
          </nav>

          <div className="hidden items-center gap-2 lg:flex">
            <ThemeToggle />
            <AuthControl />
          </div>

          <div className="flex items-center gap-2 lg:hidden">
            <ThemeToggle />
            <button
              type="button"
              aria-label={menuOpen ? "Close menu" : "Open menu"}
              aria-expanded={menuOpen}
              onClick={() => setMenuOpen((v) => !v)}
              className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-border text-content-muted hover:bg-surface-muted hover:text-content"
            >
              {menuOpen ? <Icon.close /> : <Icon.menu />}
            </button>
          </div>
        </div>

        {menuOpen && (
          <div className="border-t border-border bg-surface lg:hidden">
            <nav
              className="mx-auto flex max-w-7xl flex-col gap-1 px-4 py-3 sm:px-6"
              aria-label="Primary"
            >
              <p className="px-3 pb-1 pt-2 text-xs font-semibold uppercase tracking-wide text-content-subtle">
                Residents
              </p>
              <NavLinks
                items={RESIDENT}
                pathname={pathname}
                variant="mobile"
                onNavigate={() => setMenuOpen(false)}
              />
              <p className="px-3 pb-1 pt-3 text-xs font-semibold uppercase tracking-wide text-content-subtle">
                Staff
              </p>
              <NavLinks
                items={STAFF}
                pathname={pathname}
                variant="mobile"
                onNavigate={() => setMenuOpen(false)}
              />
              <div className="mt-2 border-t border-border pt-3">
                <AuthControl
                  variant="mobile"
                  onNavigate={() => setMenuOpen(false)}
                />
              </div>
            </nav>
          </div>
        )}
      </header>

      <main className="flex-1 py-8">{children}</main>

      <footer className="border-t border-border py-6">
        <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-2 px-4 text-xs text-content-subtle sm:flex-row sm:px-6">
          <span>CivicRoute AI — agentic civic complaint routing.</span>
          <span>Human review required for every AI recommendation.</span>
        </div>
      </footer>
    </div>
  );
}
