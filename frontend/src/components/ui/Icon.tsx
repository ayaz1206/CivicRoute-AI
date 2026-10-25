import { cn } from "@/lib/cn";

/**
 * Minimal inline SVG icon set (no icon dependency). Each icon inherits
 * currentColor and sizes via className. Decorative by default (aria-hidden);
 * pass a title for meaningful icons.
 */
type IconProps = { className?: string; title?: string };

function base(path: React.ReactNode, { className, title }: IconProps) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.8}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={cn("h-5 w-5 shrink-0", className)}
      aria-hidden={title ? undefined : true}
      role={title ? "img" : undefined}
    >
      {title && <title>{title}</title>}
      {path}
    </svg>
  );
}

export const Icon = {
  menu: (p: IconProps) => base(<><path d="M4 6h16" /><path d="M4 12h16" /><path d="M4 18h16" /></>, p),
  close: (p: IconProps) => base(<><path d="M6 6l12 12" /><path d="M18 6 6 18" /></>, p),
  check: (p: IconProps) => base(<path d="M20 6 9 17l-5-5" />, p),
  alert: (p: IconProps) => base(<><path d="M12 9v4" /><path d="M12 17h.01" /><path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z" /></>, p),
  info: (p: IconProps) => base(<><circle cx="12" cy="12" r="9" /><path d="M12 8h.01" /><path d="M11 12h1v4h1" /></>, p),
  search: (p: IconProps) => base(<><circle cx="11" cy="11" r="7" /><path d="m21 21-4.3-4.3" /></>, p),
  pin: (p: IconProps) => base(<><path d="M12 21s-7-5.5-7-11a7 7 0 1 1 14 0c0 5.5-7 11-7 11Z" /><circle cx="12" cy="10" r="2.5" /></>, p),
  clipboard: (p: IconProps) => base(<><rect x="8" y="4" width="8" height="4" rx="1" /><path d="M9 4H7a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V6a2 2 0 0 0-2-2h-2" /></>, p),
  chart: (p: IconProps) => base(<><path d="M3 3v18h18" /><rect x="7" y="12" width="3" height="6" /><rect x="12" y="8" width="3" height="10" /><rect x="17" y="5" width="3" height="13" /></>, p),
  sparkles: (p: IconProps) => base(<><path d="M12 3v4M12 17v4M3 12h4M17 12h4" /><path d="M12 8l1.5 2.5L16 12l-2.5 1.5L12 16l-1.5-2.5L8 12l2.5-1.5Z" /></>, p),
  inbox: (p: IconProps) => base(<><path d="M22 12h-6l-2 3h-4l-2-3H2" /><path d="M5 5h14l3 7v6a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1v-6Z" /></>, p),
  shield: (p: IconProps) => base(<path d="M12 3 4 6v6c0 5 3.5 8 8 9 4.5-1 8-4 8-9V6Z" />, p),
  user: (p: IconProps) => base(<><circle cx="12" cy="8" r="4" /><path d="M4 21a8 8 0 0 1 16 0" /></>, p),
  sun: (p: IconProps) => base(<><circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M4 12H2M22 12h-2M5 5l1.5 1.5M17.5 17.5 19 19M19 5l-1.5 1.5M6.5 17.5 5 19" /></>, p),
  moon: (p: IconProps) => base(<path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8Z" />, p),
  logout: (p: IconProps) => base(<><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" /><path d="M16 17l5-5-5-5" /><path d="M21 12H9" /></>, p),
  arrowRight: (p: IconProps) => base(<><path d="M5 12h14" /><path d="m13 6 6 6-6 6" /></>, p),
};
