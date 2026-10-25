"use client";

import { useEffect, useState } from "react";
import { Icon } from "@/components/ui/Icon";

const KEY = "civicroute_theme";

function apply(theme: "light" | "dark") {
  document.documentElement.classList.toggle("dark", theme === "dark");
}

export function ThemeToggle({ className }: { className?: string }) {
  const [theme, setTheme] = useState<"light" | "dark">("light");

  useEffect(() => {
    const stored = window.localStorage.getItem(KEY) as "light" | "dark" | null;
    const initial = stored ?? "light"; // light is the primary theme
    setTheme(initial);
    apply(initial);
  }, []);

  function toggle() {
    const next = theme === "dark" ? "light" : "dark";
    setTheme(next);
    apply(next);
    window.localStorage.setItem(KEY, next);
  }

  return (
    <button
      type="button"
      onClick={toggle}
      aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
      className={
        "inline-flex h-9 w-9 items-center justify-center rounded-lg border border-border " +
        "text-content-muted transition-colors hover:bg-surface-muted hover:text-content " +
        (className ?? "")
      }
    >
      {theme === "dark" ? (
        <Icon.sun className="h-4.5 w-4.5" />
      ) : (
        <Icon.moon className="h-4.5 w-4.5" />
      )}
    </button>
  );
}
