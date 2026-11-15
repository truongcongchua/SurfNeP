import { cva } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium whitespace-nowrap",
  {
    variants: {
      variant: {
        default: "bg-accent text-muted-foreground",
        easy: "bg-[var(--ok-bg)] text-[var(--easy)]",
        medium: "bg-[var(--warn-bg)] text-[var(--medium)]",
        hard: "bg-[var(--bad-bg)] text-[var(--hard)]",
        ok: "bg-[var(--ok-bg)] text-[var(--easy)]",
        warn: "bg-[var(--warn-bg)] text-[var(--medium)]",
        bad: "bg-[var(--bad-bg)] text-[var(--hard)]",
      },
    },
    defaultVariants: { variant: "default" },
  }
);

export function Badge({ className, variant, ...props }) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />;
}
