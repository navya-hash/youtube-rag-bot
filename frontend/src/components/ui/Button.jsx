import { forwardRef } from "react";
import { cn } from "@/lib/utils/cn";
import { Loader2 } from "lucide-react";

export const Button = forwardRef(function Button(
  {
    className,
    variant = "primary",
    size = "md",
    isLoading = false,
    disabled = false,
    children,
    type = "button",
    ...props
  },
  ref
) {
  const baseStyles =
    "inline-flex items-center justify-center font-medium transition-all active:scale-[0.98] disabled:pointer-events-none disabled:opacity-50 select-none rounded-xl";

  const variants = {
    primary:
      "bg-indigo-600 text-white hover:bg-indigo-500 shadow-md shadow-indigo-600/20 hover:shadow-indigo-500/30",
    secondary:
      "bg-[#131B2E] text-slate-200 border border-slate-800 hover:bg-slate-800/80 hover:text-white hover:border-slate-700",
    outline:
      "bg-transparent border border-slate-800 text-slate-300 hover:bg-[#131B2E] hover:text-white hover:border-slate-700",
    ghost:
      "bg-transparent text-slate-400 hover:bg-[#131B2E] hover:text-white",
    danger:
      "bg-rose-600/10 border border-rose-500/20 text-rose-400 hover:bg-rose-600/20 hover:border-rose-500/30",
  };

  const sizes = {
    sm: "px-3 py-1.5 text-xs gap-1.5",
    md: "px-4 py-2 text-sm gap-2",
    lg: "px-5 py-2.5 text-base gap-2.5",
    icon: "h-9 w-9 p-0",
    "icon-sm": "h-7 w-7 p-0",
  };

  return (
    <button
      ref={ref}
      type={type}
      disabled={disabled || isLoading}
      className={cn(baseStyles, variants[variant], sizes[size], className)}
      {...props}
    >
      {isLoading && <Loader2 className="h-4 w-4 animate-spin" />}
      {children}
    </button>
  );
});

