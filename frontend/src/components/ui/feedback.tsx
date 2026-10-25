import { cn } from "@/lib/cn";

/** Skeleton line / block for loading states. */
export function Skeleton({ className }: { className?: string }) {
  return <div className={cn("skeleton rounded-md", className)} aria-hidden />;
}

/** Empty-state panel with optional icon and action. */
export function EmptyState({
  icon,
  title,
  description,
  action,
  tone = "neutral",
  className,
}: {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  action?: React.ReactNode;
  tone?: "neutral" | "success";
  className?: string;
}) {
  const toneCls =
    tone === "success"
      ? "border-emerald-200 bg-emerald-50 dark:border-emerald-500/30 dark:bg-emerald-500/10"
      : "border-border bg-surface-muted";
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center rounded-xl border border-dashed px-6 py-10 text-center",
        toneCls,
        className,
      )}
    >
      {icon && (
        <div
          className={cn(
            "mb-3",
            tone === "success"
              ? "text-emerald-500"
              : "text-content-subtle",
          )}
          aria-hidden
        >
          {icon}
        </div>
      )}
      <p className="font-medium text-content">{title}</p>
      {description && (
        <p className="mt-1 max-w-sm text-sm text-content-muted">{description}</p>
      )}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
