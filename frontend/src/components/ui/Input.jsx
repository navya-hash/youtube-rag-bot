import { forwardRef } from "react";
import { cn } from "@/lib/utils/cn";

export const Input = forwardRef(function Input(
  { className, type = "text", error, ...props },
  ref
) {
  return (
    <div className="w-full">
      <input
        type={type}
        ref={ref}
        className={cn(
          "w-full rounded-xl border border-slate-800 bg-[#0F1626] px-3.5 py-2 text-sm text-[#F8FAFC] placeholder-slate-500 shadow-sm transition-colors focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 disabled:cursor-not-allowed disabled:opacity-50",
          error && "border-rose-500/80 focus:border-rose-500 focus:ring-rose-500",
          className
        )}
        {...props}
      />
      {error && (
        <p className="mt-1.5 text-xs text-rose-400 font-medium">{error}</p>
      )}
    </div>
  );
});

