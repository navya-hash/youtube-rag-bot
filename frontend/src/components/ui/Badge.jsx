import { cn } from "@/lib/utils/cn";

export function Badge({ children, variant = "default", className }) {
  const variants = {
    default:
      "border-slate-700/80 bg-[#0A0F1D] text-slate-300 shadow-sm",
    success:
      "border-emerald-500/40 bg-[#0A0F1D] text-emerald-400 shadow-sm",
    warning:
      "border-amber-500/40 bg-[#0A0F1D] text-amber-400 shadow-sm",
    danger:
      "border-rose-500/40 bg-[#0A0F1D] text-rose-400 shadow-sm",
    info:
      "border-sky-500/40 bg-[#0A0F1D] text-sky-400 shadow-sm",
    accent:
      "border-indigo-500/40 bg-[#0A0F1D] text-indigo-300 shadow-sm",
  };

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-semibold tracking-wide",
        variants[variant],
        className
      )}
    >
      {children}
    </span>
  );
}

