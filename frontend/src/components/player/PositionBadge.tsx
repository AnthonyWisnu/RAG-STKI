import { getPositionCode, getPositionTextClass, cn } from "@/lib/utils";

type PositionBadgeProps = {
  position?: string | null;
  className?: string;
};

export function PositionBadge({ position, className }: PositionBadgeProps) {
  const code = getPositionCode(position);

  return (
    <span
      className={cn(
        "inline-flex items-center rounded-panel border border-current bg-background-tertiary px-2 py-1 font-mono text-xs",
        getPositionTextClass(position),
        className
      )}
    >
      {code}
    </span>
  );
}
