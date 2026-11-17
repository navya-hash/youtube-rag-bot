"use client";

import { useState, useRef, useEffect } from "react";
import { ArrowUp, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils/cn";

export function ChatInput({ onSendMessage, isLoading = false, disabled = false, placeholder = "Ask anything about the video..." }) {
  const [input, setInput] = useState("");
  const textareaRef = useRef(null);

  // Auto-resize textarea height as user types
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(
        textareaRef.current.scrollHeight,
        200
      )}px`;
    }
  }, [input]);

  function handleKeyDown(event) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      handleSubmit();
    }
  }

  function handleSubmit() {
    const trimmed = input.trim();
    if (!trimmed || isLoading || disabled) return;

    onSendMessage(trimmed);
    setInput("");

    // Reset height
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  }

  return (
    <div className="w-full max-w-3xl mx-auto px-4 pb-4">
      <div className="relative flex flex-col rounded-2xl border border-slate-800 bg-[#0F1626] shadow-xl focus-within:border-indigo-500/80 focus-within:ring-1 focus-within:ring-indigo-500/50 transition-all">
        <textarea
          ref={textareaRef}
          rows={1}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled || isLoading}
          placeholder={placeholder}
          className="w-full resize-none bg-transparent px-4 py-3.5 text-sm text-[#F8FAFC] placeholder-slate-500 focus:outline-none max-h-48 overflow-y-auto leading-relaxed"
        />

        <div className="flex items-center justify-between px-3 pb-2.5 pt-1 border-t border-slate-800/40 text-xs text-slate-500">
          <span className="hidden sm:inline">
            Use <kbd className="px-1.5 py-0.5 rounded bg-[#131B2E] border border-slate-700 text-[10px] text-slate-400 font-mono">Enter</kbd> to send, <kbd className="px-1.5 py-0.5 rounded bg-[#131B2E] border border-slate-700 text-[10px] text-slate-400 font-mono">Shift + Enter</kbd> for newline
          </span>

          <div className="flex items-center gap-2 ml-auto">
            <button
              onClick={handleSubmit}
              disabled={!input.trim() || isLoading || disabled}
              className={cn(
                "flex h-8 w-8 items-center justify-center rounded-xl transition-all shadow-md",
                input.trim() && !isLoading && !disabled
                  ? "bg-indigo-600 text-white hover:bg-indigo-500 shadow-indigo-600/20 active:scale-95"
                  : "bg-slate-800/60 text-slate-500 cursor-not-allowed"
              )}
              title="Send message"
            >
              {isLoading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <ArrowUp className="h-4 w-4" />
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

