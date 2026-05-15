import { cn } from "@/lib/utils";

type StatBadgeProps = {
  label: string;
  value: string | number;
  className?: string;
};

export function StatBadge({ label, value, className }: StatBadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex min-w-16 flex-col rounded-panel border border-border bg-background-primary px-3 py-2",
        className
      )}
    >
      <span className="text-[11px] uppercase tracking-widest text-text-secondary">
        {label}
      </span>
      <span className="font-mono text-sm text-text-primary">{value}</span>
    </span>
  );
}
