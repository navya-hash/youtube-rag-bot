"use client";

import { useState } from "react";
import { Modal } from "@/components/ui/Modal";
import { SummaryViewer } from "./SummaryViewer";
import { useVideoSummary } from "@/hooks/useVideoSummary";
import { SUPPORTED_LANGUAGES } from "@/lib/api/chats";
import { Languages } from "lucide-react";

export function SummaryModal({ isOpen, onClose, video, defaultLanguage = "English" }) {
  const [selectedLanguage, setSelectedLanguage] = useState(defaultLanguage);

  const {
    summary,
    isLoading,
    requestSummary,
    isRequesting,
    downloadPdf,
    isDownloadingPdf,
  } = useVideoSummary(video?.id, selectedLanguage);

  const title = video?.title || `Video Summary (${video?.youtube_video_id})`;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={title}
      description="Asynchronous Celery summary with key takeaways and downloadable PDF."
      className="max-w-2xl max-h-[85vh] overflow-y-auto"
    >
      <div className="space-y-4">
        {/* Language Selector */}
        <div className="flex items-center justify-between gap-3 rounded-xl border border-slate-800 bg-[#131B2E] px-3.5 py-2">
          <div className="flex items-center gap-2 text-xs font-medium text-slate-300">
            <Languages className="h-4 w-4 text-indigo-400" />
            <span>Summary Language</span>
          </div>

          <select
            value={selectedLanguage}
            onChange={(e) => setSelectedLanguage(e.target.value)}
            className="rounded-lg border border-slate-700 bg-[#0F1626] px-2.5 py-1 text-xs text-white focus:border-indigo-500 focus:outline-none"
          >
            {SUPPORTED_LANGUAGES.map((lang) => (
              <option key={lang} value={lang}>
                {lang}
              </option>
            ))}
          </select>
        </div>

        {/* Content Viewer */}
        <SummaryViewer
          summary={summary}
          isLoading={isLoading}
          onGenerateSummary={() => requestSummary({ targetLanguage: selectedLanguage })}
          isGenerating={isRequesting}
          onDownloadPdf={() => downloadPdf({ targetLanguage: selectedLanguage })}
          isDownloadingPdf={isDownloadingPdf}
        />
      </div>
    </Modal>
  );
}

