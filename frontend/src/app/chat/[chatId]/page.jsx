"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import { Header } from "@/components/layout/Header";
import { ChatWorkspace } from "@/components/chat/ChatWorkspace";
import { VideoContextPanel } from "@/components/video/VideoContextPanel";
import { useChatDetail } from "@/hooks/useChatDetail";
import { useChatVideos } from "@/hooks/useChatVideos";
import { useChats } from "@/hooks/useChats";

export default function ChatDetailPage() {
  const params = useParams();
  const chatId = params?.chatId;

  const [isVideoPanelOpen, setIsVideoPanelOpen] = useState(true);
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false);

  // Chat details and messaging
  const {
    chat,
    isLoading: isLoadingChat,
    askQuestion,
    isAsking,
  } = useChatDetail(chatId);

  // Associated videos for this chat
  const {
    videos,
    isLoading: isLoadingVideos,
    ingestVideo,
    removeVideo,
  } = useChatVideos(chatId);

  // Chat metadata updates (title, language)
  const { updateTitle, updateLanguage } = useChats();

  async function handleSendMessage(question) {
    if (!question || isAsking) return;
    try {
      await askQuestion({ question });
    } catch (err) {
      console.error("Failed to ask question:", err);
    }
  }

  return (
    <div className="flex flex-1 flex-col h-full overflow-hidden">
      {/* Header */}
      <Header
        chat={chat}
        videoCount={videos.length}
        isVideoPanelOpen={isVideoPanelOpen}
        onToggleVideoPanel={() => setIsVideoPanelOpen(!isVideoPanelOpen)}
        onOpenMobileSidebar={() => setIsMobileSidebarOpen(true)}
        onUpdateTitle={(title) => updateTitle({ chatId, title })}
        onUpdateLanguage={(language) => updateLanguage({ chatId, language })}
      />

      {/* Main Content Area: Chat Workspace + Video Context Panel */}
      <div className="flex flex-1 overflow-hidden relative">
        <ChatWorkspace
          chat={chat}
          messages={chat?.messages || []}
          isLoadingMessages={isLoadingChat}
          isAsking={isAsking}
          onSendMessage={handleSendMessage}
          onOpenAddVideo={() => setIsVideoPanelOpen(true)}
          videoCount={videos.length}
        />

        <VideoContextPanel
          isOpen={isVideoPanelOpen}
          onClose={() => setIsVideoPanelOpen(false)}
          videos={videos}
          isLoading={isLoadingVideos}
          onIngestVideo={ingestVideo}
          onRemoveVideo={removeVideo}
          chatLanguage={chat?.output_language || "English"}
        />
      </div>
    </div>
  );
}

