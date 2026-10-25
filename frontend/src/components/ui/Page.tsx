import { cn } from "@/lib/cn";

/** Consistent page container with responsive width + padding. */
export function Container({
  size = "default",
  className,
  children,
}: {
  size?: "narrow" | "default" | "wide";
  className?: string;
  children: React.ReactNode;
}) {
  const widths = {
    narrow: "max-w-2xl",
    default: "max-w-5xl",
    wide: "max-w-7xl",
  };
  return (
    <div className={cn("mx-auto w-full px-4 sm:px-6", widths[size], className)}>
      {children}
    </div>
  );
}

/** Page header with eyebrow/title/description and optional actions. */
export function PageHeader({
  title,
  description,
  eyebrow,
  actions,
  className,
}: {
  title: string;
  description?: string;
  eyebrow?: string;
  actions?: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between",
        className,
      )}
    >
      <div>
        {eyebrow && (
          <p className="text-xs font-semibold uppercase tracking-wide text-brand-600 dark:text-brand-400">
            {eyebrow}
          </p>
        )}
        <h1 className="mt-1 text-2xl font-bold tracking-tight text-content">
          {title}
        </h1>
        {description && (
          <p className="mt-1 max-w-2xl text-sm text-content-muted">
            {description}
          </p>
        )}
      </div>
      {actions && <div className="flex shrink-0 gap-2">{actions}</div>}
    </div>
  );
}
