"use client";

import { useEffect, useRef } from "react";
import { MessageBubble } from "./MessageBubble";
import { WelcomeState } from "./WelcomeState";
import { ChatInput } from "./ChatInput";
import { Loader2, Bot } from "lucide-react";

export function ChatWorkspace({
  chat,
  messages = [],
  isLoadingMessages = false,
  isAsking = false,
  onSendMessage,
  onOpenAddVideo,
  videoCount = 0,
}) {
  const messagesEndRef = useRef(null);

  // Auto-scroll to bottom on new messages or while asking
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isAsking]);

  return (
    <div className="flex flex-1 flex-col h-[calc(100vh-4rem)] overflow-hidden bg-[#090D16]">
      {/* Scrollable Messages Area */}
      <div className="flex-1 overflow-y-auto">
        {isLoadingMessages ? (
          <div className="flex h-full items-center justify-center text-slate-500">
            <Loader2 className="h-6 w-6 animate-spin text-indigo-500 mb-2" />
          </div>
        ) : messages.length === 0 ? (
          <WelcomeState
            onSelectPrompt={onSendMessage}
            onOpenAddVideo={onOpenAddVideo}
            videoCount={videoCount}
          />
        ) : (
          <div className="flex flex-col pb-6">
            {messages.map((message) => (
              <MessageBubble key={message.id} message={message} />
            ))}

            {/* AI Generation Loading State */}
            {isAsking && (
              <div className="flex w-full gap-4 px-4 py-6 bg-[#0A0F1D]/50 border-y border-slate-800/40">
                <div className="flex w-full max-w-3xl gap-4">
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-gradient-to-tr from-indigo-600 to-indigo-500 text-white shadow-md shadow-indigo-600/20">
                    <Bot className="h-4 w-4" />
                  </div>
                  <div className="flex items-center gap-3 text-xs text-slate-400 py-2">
                    <Loader2 className="h-4 w-4 animate-spin text-indigo-400" />
                    <span className="font-medium animate-pulse">
                      Analyzing video context and generating response...
                    </span>
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Fixed Bottom Chat Input */}
      <div className="shrink-0 pt-2">
        <ChatInput
          onSendMessage={onSendMessage}
          isLoading={isAsking}
          disabled={isLoadingMessages}
          placeholder={
            videoCount > 0
              ? "Ask a question about the attached video(s)..."
              : "Attach a YouTube video in the right panel to ask questions..."
          }
        />
      </div>
    </div>
  );
}

