import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { User, Bot, Copy, Check, Sparkles, BookOpen } from "lucide-react";
import { CitationCard } from "./CitationCard";
import { formatDate } from "@/lib/utils/formatters";
import { cn } from "@/lib/utils/cn";

export function MessageBubble({ message }) {
  const [copied, setCopied] = useState(false);
  const isUser = message.role === "user";
  const citations = message.citations || [];

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(message.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error("Failed to copy:", err);
    }
  }

  return (
    <div
      className={cn(
        "flex w-full gap-4 px-4 py-6 transition-colors",
        isUser ? "bg-transparent justify-end" : "bg-[#0A0F1D]/50 border-y border-slate-800/40"
      )}
    >
      <div
        className={cn(
          "flex w-full max-w-3xl gap-4",
          isUser ? "flex-row-reverse justify-start" : "flex-row"
        )}
      >
        {/* Avatar */}
        <div
          className={cn(
            "flex h-8 w-8 shrink-0 items-center justify-center rounded-xl shadow-md",
            isUser
              ? "bg-[#1E293B] text-slate-300 border border-slate-700"
              : "bg-gradient-to-tr from-indigo-600 to-indigo-500 text-white shadow-indigo-600/20"
          )}
        >
          {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
        </div>

        {/* Message Content Container */}
        <div className={cn("flex flex-col overflow-hidden", isUser ? "items-end" : "items-start", "flex-1")}>
          {/* Header Info */}
          <div className="flex items-center gap-2 mb-1.5 text-xs text-slate-500">
            <span className="font-semibold text-slate-300">
              {isUser ? "You" : "Assistant"}
            </span>
            {message.output_language && !isUser && (
              <span className="rounded bg-indigo-500/10 px-1.5 py-0.5 text-[10px] font-medium text-indigo-300 border border-indigo-500/20">
                {message.output_language}
              </span>
            )}
            {message.created_at && (
              <span className="text-[10px]">
                {formatDate(message.created_at)}
              </span>
            )}
          </div>

          {/* Text Bubble */}
          <div
            className={cn(
              "overflow-hidden rounded-2xl text-sm leading-relaxed",
              isUser
                ? "bg-[#131B2E] text-slate-100 px-4 py-3 border border-slate-800/80 max-w-xl"
                : "w-full text-slate-200"
            )}
          >
            {isUser ? (
              <p className="whitespace-pre-wrap">{message.content}</p>
            ) : (
              <div className="prose prose-invert prose-indigo max-w-none text-sm leading-relaxed space-y-3">
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  components={{
                    h1: ({ node, ...props }) => (
                      <h1 className="text-lg font-bold text-white mt-4 mb-2 border-b border-slate-800 pb-1" {...props} />
                    ),
                    h2: ({ node, ...props }) => (
                      <h2 className="text-base font-semibold text-white mt-3 mb-2" {...props} />
                    ),
                    h3: ({ node, ...props }) => (
                      <h3 className="text-sm font-semibold text-indigo-200 mt-2 mb-1" {...props} />
                    ),
                    p: ({ node, ...props }) => (
                      <p className="mb-2 leading-relaxed text-slate-200" {...props} />
                    ),
                    ul: ({ node, ...props }) => (
                      <ul className="list-disc pl-5 mb-2 space-y-1 text-slate-300" {...props} />
                    ),
                    ol: ({ node, ...props }) => (
                      <ol className="list-decimal pl-5 mb-2 space-y-1 text-slate-300" {...props} />
                    ),
                    li: ({ node, ...props }) => (
                      <li className="leading-relaxed" {...props} />
                    ),
                    code: ({ node, inline, ...props }) =>
                      inline ? (
                        <code className="rounded bg-[#131B2E] px-1.5 py-0.5 font-mono text-xs text-indigo-300 border border-slate-800" {...props} />
                      ) : (
                        <pre className="overflow-x-auto rounded-xl border border-slate-800 bg-[#090D16] p-3 text-xs font-mono text-slate-200 my-2">
                          <code {...props} />
                        </pre>
                      ),
                    blockquote: ({ node, ...props }) => (
                      <blockquote className="border-l-2 border-indigo-500 pl-3 italic text-slate-400 my-2" {...props} />
                    ),
                    table: ({ node, ...props }) => (
                      <div className="overflow-x-auto my-3">
                        <table className="min-w-full divide-y divide-slate-800 border border-slate-800 text-xs text-left" {...props} />
                      </div>
                    ),
                    th: ({ node, ...props }) => (
                      <th className="bg-[#131B2E] px-3 py-2 font-semibold text-slate-200" {...props} />
                    ),
                    td: ({ node, ...props }) => (
                      <td className="px-3 py-2 border-t border-slate-800/60" {...props} />
                    ),
                  }}
                >
                  {message.content}
                </ReactMarkdown>
              </div>
            )}
          </div>

          {/* Assistant Actions: Copy button */}
          {!isUser && (
            <div className="mt-2 flex items-center gap-2">
              <button
                onClick={handleCopy}
                className="flex items-center gap-1.5 rounded-lg px-2 py-1 text-xs text-slate-400 hover:bg-[#131B2E] hover:text-slate-200 transition-colors"
                title="Copy response to clipboard"
              >
                {copied ? (
                  <>
                    <Check className="h-3.5 w-3.5 text-emerald-400" />
                    <span className="text-emerald-400">Copied</span>
                  </>
                ) : (
                  <>
                    <Copy className="h-3.5 w-3.5" />
                    <span>Copy</span>
                  </>
                )}
              </button>
            </div>
          )}

          {/* Verified Video Citations */}
          {!isUser && citations.length > 0 && (
            <div className="mt-4 w-full rounded-2xl border border-slate-800/80 bg-[#0A0F1D] p-3.5 shadow-sm">
              <div className="flex items-center gap-2 mb-3 text-xs font-semibold text-slate-300">
                <BookOpen className="h-4 w-4 text-indigo-400" />
                <span>Verified Video Sources</span>
                <span className="rounded-full bg-indigo-500/10 px-2 py-0.5 text-[10px] text-indigo-300 border border-indigo-500/20">
                  {citations.length} cited
                </span>
              </div>

              <div className="grid grid-cols-1 gap-2.5">
                {citations.map((citation, idx) => (
                  <CitationCard key={idx} citation={citation} index={idx} />
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

