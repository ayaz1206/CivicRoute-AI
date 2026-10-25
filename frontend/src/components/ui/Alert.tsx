import { cn } from "@/lib/cn";
import { Icon } from "./Icon";

type Tone = "info" | "success" | "warning" | "error";

const TONES: Record<Tone, { box: string; icon: React.ReactNode }> = {
  info: {
    box: "border-sky-200 bg-sky-50 text-sky-800 dark:border-sky-500/30 dark:bg-sky-500/10 dark:text-sky-200",
    icon: <Icon.info className="h-5 w-5" />,
  },
  success: {
    box: "border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-500/30 dark:bg-emerald-500/10 dark:text-emerald-200",
    icon: <Icon.check className="h-5 w-5" />,
  },
  warning: {
    box: "border-amber-200 bg-amber-50 text-amber-900 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-200",
    icon: <Icon.alert className="h-5 w-5" />,
  },
  error: {
    box: "border-red-200 bg-red-50 text-red-800 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-200",
    icon: <Icon.alert className="h-5 w-5" />,
  },
};

export function Alert({
  tone = "info",
  title,
  children,
  action,
  role,
  className,
}: {
  tone?: Tone;
  title?: React.ReactNode;
  children?: React.ReactNode;
  action?: React.ReactNode;
  role?: "alert" | "status";
  className?: string;
}) {
  const t = TONES[tone];
  return (
    <div
      role={role ?? (tone === "error" ? "alert" : "status")}
      className={cn("flex gap-3 rounded-xl border p-3.5 text-sm", t.box, className)}
    >
      <span className="mt-0.5 shrink-0" aria-hidden>
        {t.icon}
      </span>
      <div className="flex-1">
        {title && <p className="font-semibold">{title}</p>}
        {children && <div className={cn(Boolean(title) && "mt-0.5")}>{children}</div>}
        {action && <div className="mt-2">{action}</div>}
      </div>
    </div>
  );
}
