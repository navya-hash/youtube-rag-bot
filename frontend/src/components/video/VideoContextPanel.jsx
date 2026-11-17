"use client";

import { useState } from "react";
import { Plus, X, Youtube, Loader2 } from "lucide-react";
import { VideoCard } from "./VideoCard";
import { AddVideoModal } from "./AddVideoModal";
import { Modal } from "@/components/ui/Modal";
import { Button } from "@/components/ui/Button";
import { SummaryModal } from "@/components/summary/SummaryModal";
import { cn } from "@/lib/utils/cn";

export function VideoContextPanel({
  isOpen,
  onClose,
  videos = [],
  isLoading = false,
  onIngestVideo,
  onRemoveVideo,
  chatLanguage = "English",
}) {
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [removingVideo, setRemovingVideo] = useState(null);
  const [summarizingVideo, setSummarizingVideo] = useState(null);
  const [isDeleting, setIsDeleting] = useState(false);

  async function handleConfirmRemove() {
    if (!removingVideo) return;
    setIsDeleting(true);
    try {
      await onRemoveVideo(removingVideo.id);
      setRemovingVideo(null);
    } catch (err) {
      console.error("Failed to remove video:", err);
    } finally {
      setIsDeleting(false);
    }
  }

  return (
    <>
      <aside
        className={cn(
          "fixed inset-y-0 right-0 z-30 flex flex-col border-l border-slate-800 bg-[#0A0F1D] transition-all duration-300 ease-in-out lg:static",
          isOpen ? "w-80 translate-x-0" : "w-0 translate-x-full lg:w-0 overflow-hidden"
        )}
      >
        {/* Panel Header */}
        <div className="flex h-16 shrink-0 items-center justify-between px-4 border-b border-slate-800/80">
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-white tracking-tight">
              Video Context
            </span>
            <span className="rounded-full bg-indigo-500/10 px-2 py-0.5 text-[11px] font-bold text-indigo-300 border border-indigo-500/20">
              {videos.length}
            </span>
          </div>

          <div className="flex items-center gap-1">
            <button
              onClick={() => setIsAddModalOpen(true)}
              className="flex items-center gap-1.5 rounded-lg bg-indigo-600/20 px-2.5 py-1 text-xs font-medium text-indigo-300 hover:bg-indigo-600/30 transition-colors"
              title="Add YouTube video"
            >
              <Plus className="h-3.5 w-3.5" />
              <span>Add</span>
            </button>

            <button
              onClick={onClose}
              className="rounded-lg p-1 text-slate-400 hover:bg-[#131B2E] hover:text-white transition-colors"
              title="Close panel"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>

        {/* Video List */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3.5">
          {isLoading ? (
            <div className="flex flex-col items-center justify-center py-16 text-slate-500">
              <Loader2 className="h-5 w-5 animate-spin" />
              <span className="mt-2 text-xs">Loading videos...</span>
            </div>
          ) : videos.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 px-4 text-center rounded-2xl border border-dashed border-slate-800 p-6">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-slate-800 text-slate-400 mb-3">
                <Youtube className="h-5 w-5" />
              </div>
              <p className="text-xs font-semibold text-slate-300">
                No videos attached
              </p>
              <p className="mt-1 text-[11px] text-slate-500">
                Add a YouTube video to allow the AI to answer questions using its transcript.
              </p>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setIsAddModalOpen(true)}
                className="mt-4 text-xs"
              >
                <Plus className="h-3.5 w-3.5" />
                Add Video URL
              </Button>
            </div>
          ) : (
            videos.map((video) => (
              <VideoCard
                key={video.id}
                video={video}
                onOpenSummary={(v) => setSummarizingVideo(v)}
                onRemoveVideo={(v) => setRemovingVideo(v)}
              />
            ))
          )}
        </div>
      </aside>

      {/* Add Video Modal */}
      <AddVideoModal
        isOpen={isAddModalOpen}
        onClose={() => setIsAddModalOpen(false)}
        onIngest={onIngestVideo}
      />

      {/* Remove Video Confirmation Modal */}
      <Modal
        isOpen={Boolean(removingVideo)}
        onClose={() => setRemovingVideo(null)}
        title="Remove Video from Chat"
        description={`Are you sure you want to remove this video (${removingVideo?.youtube_video_id}) from this chat? The chat will no longer use this video's transcript for answering questions.`}
      >
        <div className="flex justify-end gap-3 mt-6">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => setRemovingVideo(null)}
            disabled={isDeleting}
          >
            Cancel
          </Button>
          <Button
            variant="danger"
            size="sm"
            isLoading={isDeleting}
            onClick={handleConfirmRemove}
          >
            Remove Video
          </Button>
        </div>
      </Modal>

      {/* Summary Workspace Modal */}
      {summarizingVideo && (
        <SummaryModal
          isOpen={Boolean(summarizingVideo)}
          onClose={() => setSummarizingVideo(null)}
          video={summarizingVideo}
          defaultLanguage={chatLanguage}
        />
      )}
    </>
  );
}

