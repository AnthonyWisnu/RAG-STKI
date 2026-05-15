"use client";

import { type ButtonHTMLAttributes, forwardRef } from "react";

import { cn } from "@/lib/utils";

type ButtonVariant = "primary" | "secondary" | "ghost" | "icon";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
};

const variantClasses: Record<ButtonVariant, string> = {
  primary:
    "border-accent bg-accent text-background-primary hover:bg-accent-hover",
  secondary:
    "border-border bg-background-secondary text-text-primary hover:bg-background-tertiary",
  ghost:
    "border-transparent bg-transparent text-text-secondary hover:bg-background-tertiary hover:text-text-primary",
  icon:
    "h-10 w-10 border-border bg-background-secondary p-0 text-text-secondary hover:bg-background-tertiary hover:text-text-primary"
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "secondary", type = "button", ...props }, ref) => (
    <button
      ref={ref}
      type={type}
      className={cn(
        "inline-flex min-h-10 items-center justify-center gap-2 rounded-panel border px-4 text-sm font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50",
        variantClasses[variant],
        className
      )}
      {...props}
    />
  )
);

Button.displayName = "Button";
