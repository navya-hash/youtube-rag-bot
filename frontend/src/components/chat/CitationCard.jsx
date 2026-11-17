import { useState } from "react";
import { ExternalLink, Play, ChevronDown, ChevronUp } from "lucide-react";
import { formatSeconds } from "@/lib/utils/formatters";
import { getYouTubeTimestampUrl } from "@/lib/utils/youtube";

export function CitationCard({ citation, index }) {
  const [isExpanded, setIsExpanded] = useState(false);

  const startSec = citation.start ?? 0;
  const endSec = citation.end ?? 0;
  const videoId = citation.youtube_video_id;
  const title = citation.video_title || `Video Source #${index + 1}`;
  const timestampUrl = getYouTubeTimestampUrl(videoId, startSec);
  const text = citation.text || "";

  return (
    <div className="rounded-xl border border-slate-800 bg-[#0F1626] p-3 text-xs shadow-sm hover:border-slate-700 transition-colors">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 overflow-hidden">
          <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-lg bg-indigo-500/10 text-indigo-400">
            <Play className="h-3 w-3 fill-current" />
          </div>
          <span className="truncate font-medium text-slate-200" title={title}>
            {title}
          </span>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <span className="font-mono text-[11px] font-medium text-indigo-300 bg-indigo-500/10 px-2 py-0.5 rounded border border-indigo-500/20">
            {formatSeconds(startSec)} - {formatSeconds(endSec)}
          </span>

          <a
            href={timestampUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="p-1 text-slate-400 hover:text-white transition-colors"
            title="Open on YouTube at this timestamp"
          >
            <ExternalLink className="h-3.5 w-3.5" />
          </a>
        </div>
      </div>

      {text && (
        <div className="mt-2.5">
          <p
            className={`text-slate-400 leading-relaxed ${
              isExpanded ? "" : "line-clamp-2"
            }`}
          >
            "{text}"
          </p>
          {text.length > 120 && (
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="mt-1 flex items-center gap-1 text-[11px] font-medium text-indigo-400 hover:text-indigo-300"
            >
              {isExpanded ? (
                <>
                  Show less <ChevronUp className="h-3 w-3" />
                </>
              ) : (
                <>
                  Show more <ChevronDown className="h-3 w-3" />
                </>
              )}
            </button>
          )}
        </div>
      )}
    </div>
  );
}

