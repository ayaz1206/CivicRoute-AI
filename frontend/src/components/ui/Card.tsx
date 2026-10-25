import { cn } from "@/lib/cn";

export function Card({
  className,
  children,
  as: Tag = "div",
}: {
  className?: string;
  children: React.ReactNode;
  as?: React.ElementType;
}) {
  return (
    <Tag
      className={cn(
        "rounded-2xl border border-border bg-surface shadow-card",
        className,
      )}
    >
      {children}
    </Tag>
  );
}

export function CardBody({
  className,
  children,
}: {
  className?: string;
  children: React.ReactNode;
}) {
  return <div className={cn("p-5", className)}>{children}</div>;
}

export function CardHeader({
  title,
  description,
  action,
}: {
  title: React.ReactNode;
  description?: React.ReactNode;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex items-start justify-between gap-4 border-b border-border px-5 py-4">
      <div>
        <h3 className="font-semibold text-content">{title}</h3>
        {description && (
          <p className="mt-0.5 text-sm text-content-muted">{description}</p>
        )}
      </div>
      {action}
    </div>
  );
}

/** Compact statistic card for dashboards. */
export function StatCard({
  label,
  value,
  hint,
  tone = "default",
}: {
  label: string;
  value: React.ReactNode;
  hint?: string;
  tone?: "default" | "success" | "warning" | "danger" | "brand";
}) {
  const tones: Record<string, string> = {
    default: "text-content",
    success: "text-emerald-600 dark:text-emerald-400",
    warning: "text-amber-600 dark:text-amber-400",
    danger: "text-red-600 dark:text-red-400",
    brand: "text-brand-600 dark:text-brand-400",
  };
  return (
    <Card>
      <CardBody>
        <div className={cn("text-2xl font-semibold tabular-nums", tones[tone])}>
          {value}
        </div>
        <div className="mt-1 text-xs font-medium uppercase tracking-wide text-content-subtle">
          {label}
        </div>
        {hint && <div className="mt-1 text-xs text-content-muted">{hint}</div>}
      </CardBody>
    </Card>
  );
}
