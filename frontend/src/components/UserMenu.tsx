"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { cn } from "@/lib/cn";
import { type CurrentUser } from "@/lib/api";
import { Icon } from "@/components/ui/Icon";
import { Badge } from "@/components/ui/Badge";

function initials(user: CurrentUser): string {
  const base = user.full_name?.trim() || user.email;
  const parts = base.split(/\s+/).filter(Boolean);
  if (parts.length >= 2) {
    return (parts[0][0] + parts[1][0]).toUpperCase();
  }
  return base.slice(0, 2).toUpperCase();
}

function displayName(user: CurrentUser): string {
  return user.full_name?.trim() || user.email.split("@")[0];
}

/**
 * Authenticated staff profile control: avatar (initials) + name button that
 * opens an accessible dropdown with identity (name, email, role) and actions.
 * `variant="mobile"` renders an expanded inline block for the mobile menu.
 */
export function UserMenu({
  user,
  onSignOut,
  variant = "desktop",
}: {
  user: CurrentUser;
  onSignOut: () => void;
  variant?: "desktop" | "mobile";
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  // Close on outside click and on Escape.
  useEffect(() => {
    if (!open) return;
    function onClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onClick);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onClick);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const avatar = (
    <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-brand-500 to-brand-700 text-xs font-semibold text-white">
      {initials(user)}
    </span>
  );

  const identity = (
    <div className="min-w-0">
      <p className="truncate text-sm font-medium text-content">
        {displayName(user)}
      </p>
      <p className="truncate text-xs text-content-subtle">{user.email}</p>
    </div>
  );

  const menuItems = (close: () => void) => (
    <>
      <Link
        href="/profile"
        role="menuitem"
        onClick={close}
        className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-content transition-colors hover:bg-surface-muted"
      >
        <Icon.user className="h-4 w-4 text-content-muted" />
        My profile
      </Link>
      <Link
        href="/staff"
        role="menuitem"
        onClick={close}
        className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-content transition-colors hover:bg-surface-muted"
      >
        <Icon.inbox className="h-4 w-4 text-content-muted" />
        Staff dashboard
      </Link>
      <button
        role="menuitem"
        onClick={() => {
          close();
          onSignOut();
        }}
        className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm text-red-600 transition-colors hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-500/10"
      >
        <Icon.logout className="h-4 w-4" />
        Sign out
      </button>
    </>
  );

  // Mobile: render identity + actions inline (no floating dropdown).
  if (variant === "mobile") {
    return (
      <div className="flex flex-col gap-1">
        <div className="flex items-center gap-3 px-3 py-2">
          {avatar}
          {identity}
          <Badge tone="brand" className="ml-auto capitalize">
            {user.role}
          </Badge>
        </div>
        {menuItems(() => {})}
      </div>
    );
  }

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="menu"
        aria-expanded={open}
        className="flex items-center gap-2 rounded-lg border border-border bg-surface px-2 py-1.5 text-sm transition-colors hover:bg-surface-muted"
      >
        {avatar}
        <span className="hidden max-w-[10rem] truncate font-medium text-content sm:inline">
          {displayName(user)}
        </span>
        <svg
          viewBox="0 0 24 24"
          className={cn(
            "h-4 w-4 text-content-muted transition-transform",
            open && "rotate-180",
          )}
          fill="none"
          stroke="currentColor"
          strokeWidth={2}
          aria-hidden
        >
          <path d="m6 9 6 6 6-6" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </button>

      {open && (
        <div
          role="menu"
          aria-label="Account menu"
          className="absolute right-0 z-50 mt-2 w-64 origin-top-right animate-fade-in rounded-xl border border-border bg-surface p-1.5 shadow-card-hover"
        >
          <div className="flex items-center gap-3 border-b border-border px-3 py-3">
            {avatar}
            <div className="min-w-0 flex-1">
              {identity}
            </div>
          </div>
          <div className="px-3 py-2">
            <Badge tone="brand" className="capitalize">
              <Icon.shield className="h-3 w-3" />
              {user.role}
            </Badge>
          </div>
          <div className="flex flex-col">{menuItems(() => setOpen(false))}</div>
        </div>
      )}
    </div>
  );
}
