import { FileText, Download, CheckCircle2, Clock, AlertCircle, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";

export function SummaryViewer({
  summary,
  isLoading,
  isPolling,
  onGenerateSummary,
  isGenerating,
  onDownloadPdf,
  isDownloadingPdf,
}) {
  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-slate-400">
        <Loader2 className="h-6 w-6 animate-spin text-indigo-500 mb-2" />
        <span className="text-xs">Checking existing summary...</span>
      </div>
    );
  }

  // Not generated yet
  if (!summary) {
    return (
      <div className="flex flex-col items-center justify-center py-12 px-4 text-center rounded-2xl border border-dashed border-slate-800 p-8">
        <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 mb-4">
          <FileText className="h-6 w-6" />
        </div>
        <h3 className="text-sm font-semibold text-white">
          No summary generated yet in this language
        </h3>
        <p className="mt-1.5 text-xs text-slate-400 max-w-sm leading-relaxed">
          Trigger the asynchronous Celery background worker to extract topics,
          key takeaways, and an executive briefing.
        </p>
        <Button
          variant="primary"
          size="md"
          isLoading={isGenerating}
          onClick={onGenerateSummary}
          className="mt-5"
        >
          <FileText className="h-4 w-4" />
          Generate Video Summary
        </Button>
      </div>
    );
  }

  // Background Processing / Pending State
  if (summary.status === "pending" || summary.status === "processing") {
    return (
      <div className="flex flex-col items-center justify-center py-16 px-4 text-center rounded-2xl border border-indigo-500/20 bg-indigo-500/5 p-8">
        <Loader2 className="h-8 w-8 animate-spin text-indigo-400 mb-4" />
        <h3 className="text-sm font-semibold text-white">
          Generating Video Summary...
        </h3>
        <p className="mt-1.5 text-xs text-slate-400 max-w-sm leading-relaxed">
          The background worker is currently analyzing the transcript and synthesizing key points. This page will automatically update once complete.
        </p>
        <div className="mt-4 flex items-center gap-2 text-[11px] text-indigo-300 font-mono">
          <Clock className="h-3.5 w-3.5 animate-pulse" />
          <span>Status: {summary.status}</span>
        </div>
      </div>
    );
  }

  // Failed State
  if (summary.status === "failed") {
    return (
      <div className="flex flex-col items-center justify-center py-12 px-4 text-center rounded-2xl border border-rose-500/20 bg-rose-500/10 p-8">
        <AlertCircle className="h-8 w-8 text-rose-400 mb-3" />
        <h3 className="text-sm font-semibold text-rose-200">
          Summarization Failed
        </h3>
        <p className="mt-1.5 text-xs text-rose-300 max-w-sm">
          {summary.error_message || "An unexpected error occurred during summarization."}
        </p>
        <Button
          variant="secondary"
          size="sm"
          isLoading={isGenerating}
          onClick={onGenerateSummary}
          className="mt-4"
        >
          Retry Summarization
        </Button>
      </div>
    );
  }

  // Completed State
  return (
    <div className="space-y-6">
      {/* Action Header: PDF Export & Model Tag */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800/80 pb-4">
        <div className="flex items-center gap-2">
          <Badge variant="success">
            <CheckCircle2 className="h-3 w-3" />
            Completed
          </Badge>
          {summary.model_name && (
            <span className="text-[11px] text-slate-500 font-mono">
              Model: {summary.model_name}
            </span>
          )}
        </div>

        <Button
          variant="secondary"
          size="sm"
          isLoading={isDownloadingPdf}
          onClick={onDownloadPdf}
        >
          <Download className="h-3.5 w-3.5 text-indigo-400" />
          Download PDF Summary
        </Button>
      </div>

      {/* Core Topics */}
      {summary.topics && summary.topics.length > 0 && (
        <div>
          <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
            Topics Covered
          </h4>
          <div className="flex flex-wrap gap-1.5">
            {summary.topics.map((topic, idx) => (
              <span
                key={idx}
                className="rounded-lg bg-[#131B2E] border border-slate-800 px-2.5 py-1 text-xs font-medium text-indigo-300"
              >
                #{topic}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Key Takeaways */}
      {summary.key_points && summary.key_points.length > 0 && (
        <div>
          <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2.5">
            Key Takeaways
          </h4>
          <ul className="space-y-2">
            {summary.key_points.map((point, idx) => (
              <li
                key={idx}
                className="flex items-start gap-2.5 text-xs text-slate-200 leading-relaxed rounded-xl bg-[#131B2E]/50 p-2.5 border border-slate-800/50"
              >
                <div className="h-1.5 w-1.5 rounded-full bg-indigo-400 mt-1.5 shrink-0" />
                <span>{point}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Executive Summary */}
      {summary.summary && (
        <div>
          <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
            Executive Summary
          </h4>
          <div className="rounded-xl border border-slate-800 bg-[#131B2E]/30 p-4 text-xs text-slate-300 leading-relaxed whitespace-pre-wrap">
            {summary.summary}
          </div>
        </div>
      )}
    </div>
  );
}

