"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@clerk/nextjs";
import { listChatVideos, removeVideoFromChat } from "@/lib/api/chats";
import { ingestVideo } from "@/lib/api/youtube";

export function useChatVideos(chatId) {
  const { getToken } = useAuth();
  const queryClient = useQueryClient();

  const videosQuery = useQuery({
    queryKey: ["chat-videos", chatId],
    queryFn: async () => {
      if (!chatId) return [];
      const token = await getToken();
      return listChatVideos(chatId, token);
    },
    enabled: Boolean(chatId),
  });

  const ingestMutation = useMutation({
    mutationFn: async ({ url, language = "en" }) => {
      const token = await getToken();
      return ingestVideo({ url, chat_id: chatId, language }, token);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["chat-videos", chatId] });
      queryClient.invalidateQueries({ queryKey: ["chat", chatId] });
    },
  });

  const removeVideoMutation = useMutation({
    mutationFn: async (videoId) => {
      const token = await getToken();
      return removeVideoFromChat(chatId, videoId, token);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["chat-videos", chatId] });
      queryClient.invalidateQueries({ queryKey: ["chat", chatId] });
    },
  });

  return {
    videos: videosQuery.data || [],
    isLoading: videosQuery.isLoading,
    isError: videosQuery.isError,
    error: videosQuery.error,
    refetch: videosQuery.refetch,
    ingestVideo: ingestMutation.mutateAsync,
    isIngesting: ingestMutation.isPending,
    ingestError: ingestMutation.error,
    removeVideo: removeVideoMutation.mutateAsync,
    isRemoving: removeVideoMutation.isPending,
  };
}

