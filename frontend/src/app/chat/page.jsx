"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Header } from "@/components/layout/Header";
import { ChatWorkspace } from "@/components/chat/ChatWorkspace";
import { useChats } from "@/hooks/useChats";

export default function NewChatPage() {
  const router = useRouter();
  const { createChat, isCreating } = useChats();
  const [isStarting, setIsStarting] = useState(false);

  async function handleStartChatWithMessage(question) {
    if (!question || isStarting || isCreating) return;
    setIsStarting(true);
    try {
      // Create chat using first few words as default title
      const title =
        question.length > 40 ? question.slice(0, 40).trim() + "..." : question;
      const newChat = await createChat({ title });
      router.push(`/chat/${newChat.id}`);
    } catch (err) {
      console.error("Failed to start chat:", err);
      setIsStarting(false);
    }
  }

  return (
    <div className="flex flex-1 flex-col h-full overflow-hidden">
      <Header
        chat={{ title: "New Conversation", output_language: "English" }}
        videoCount={0}
        isVideoPanelOpen={false}
        onToggleVideoPanel={() => {}}
        onOpenMobileSidebar={() => {}}
      />

      <div className="flex flex-1 overflow-hidden relative">
        <ChatWorkspace
          messages={[]}
          isLoadingMessages={false}
          isAsking={isStarting || isCreating}
          onSendMessage={handleStartChatWithMessage}
          onOpenAddVideo={() => {
            // Create chat first then let user add video
            handleStartChatWithMessage("Analyze YouTube video");
          }}
          videoCount={0}
        />
      </div>
    </div>
  );
}

