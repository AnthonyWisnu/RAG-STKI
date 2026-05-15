import { cn } from "@/lib/utils";

type SectionHeadingProps = {
  title: string;
  className?: string;
};

export function SectionHeading({ title, className }: SectionHeadingProps) {
  return (
    <div className={cn("flex items-center gap-3", className)}>
      <h2 className="whitespace-nowrap font-display text-xs font-bold uppercase tracking-widest text-text-secondary">
        {title}
      </h2>
      <div className="h-px flex-1 bg-border" />
    </div>
  );
}
