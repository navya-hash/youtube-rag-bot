import { useState } from "react";
import Image from "next/image";
import {
  ExternalLink,
  Trash2,
  FileText,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Youtube,
} from "lucide-react";
import { getYouTubeThumbnails } from "@/lib/utils/youtube";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";

export function VideoCard({ video, onOpenSummary, onRemoveVideo }) {
  const [imageError, setImageError] = useState(false);
  const thumbnails = getYouTubeThumbnails(video.youtube_video_id);
  const title = video.title || `YouTube Video (${video.youtube_video_id})`;

  const statusVariants = {
    completed: "success",
    processing: "warning",
    pending: "default",
    failed: "danger",
  };

  return (
    <div className="group rounded-2xl border border-slate-800 bg-[#0F1626] overflow-hidden shadow-sm hover:border-slate-700 transition-all">
      {/* Video Thumbnail */}
      <div className="relative aspect-video w-full bg-slate-900 overflow-hidden">
        {!imageError ? (
          <img
            src={thumbnails.medium}
            alt={title}
            onError={() => setImageError(true)}
            className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center bg-slate-800 text-slate-500">
            <Youtube className="h-10 w-10 text-slate-600" />
          </div>
        )}

        {/* Status Badge Overlay */}
        <div className="absolute top-2.5 left-2.5 z-10">
          <Badge
            variant={statusVariants[video.status] || "default"}
            className="shadow-md backdrop-blur-md"
          >
            {video.status === "completed" && <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400 shrink-0" />}
            {video.status === "processing" && <Loader2 className="h-3.5 w-3.5 animate-spin text-amber-400 shrink-0" />}
            {video.status === "failed" && <AlertCircle className="h-3.5 w-3.5 text-rose-400 shrink-0" />}
            <span className="capitalize">{video.status}</span>
          </Badge>
        </div>

        {/* External Link Overlay */}
        <a
          href={video.url}
          target="_blank"
          rel="noopener noreferrer"
          className="absolute top-2 right-2 rounded-lg bg-black/60 p-1.5 text-white backdrop-blur-sm opacity-0 group-hover:opacity-100 hover:bg-black/80 transition-all"
          title="Open in YouTube"
        >
          <ExternalLink className="h-3.5 w-3.5" />
        </a>
      </div>

      {/* Video Meta & Actions */}
      <div className="p-3.5">
        <h4
          className="text-xs font-semibold text-white line-clamp-2 leading-snug"
          title={title}
        >
          {title}
        </h4>

        {video.language && (
          <p className="mt-1 text-[11px] text-slate-400">
            Language: <span className="text-slate-300 uppercase font-mono">{video.language}</span>
          </p>
        )}

        {video.error_message && (
          <p className="mt-1.5 text-[11px] text-rose-400 line-clamp-2">
            {video.error_message}
          </p>
        )}

        {/* Actions Bar */}
        <div className="mt-3 flex items-center justify-between gap-2 border-t border-slate-800/80 pt-2.5">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => onOpenSummary(video)}
            className="flex-1 text-xs"
            disabled={video.status !== "completed"}
          >
            <FileText className="h-3.5 w-3.5 text-indigo-400" />
            Summarize
          </Button>

          <button
            onClick={() => onRemoveVideo(video)}
            className="rounded-xl p-2 text-slate-400 hover:bg-rose-500/10 hover:text-rose-400 transition-colors"
            title="Remove from chat"
          >
            <Trash2 className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
}

