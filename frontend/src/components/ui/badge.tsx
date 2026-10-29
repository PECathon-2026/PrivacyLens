import * as React from "react";
import { cn } from "@/lib/utils";

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "default" | "secondary" | "destructive" | "outline" | "success" | "warning" | "cyan";
}

function Badge({ className, variant = "default", ...props }: BadgeProps) {
  const variants = {
    default: "border-transparent bg-primary/20 text-primary hover:bg-primary/30 border border-primary/30",
    secondary: "border-transparent bg-secondary text-secondary-foreground hover:bg-secondary/80",
    destructive: "border-transparent bg-red-500/20 text-red-400 border border-red-500/30",
    outline: "text-foreground border border-border",
    success: "border-transparent bg-emerald-500/20 text-emerald-400 border border-emerald-500/30",
    warning: "border-transparent bg-amber-500/20 text-amber-300 border border-amber-500/30",
    cyan: "border-transparent bg-cyan-500/20 text-cyan-300 border border-cyan-500/30",
  };

  return (
    <div
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold tracking-wide transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
        variants[variant],
        className
      )}
      {...props}
    />
  );
}

export { Badge };
