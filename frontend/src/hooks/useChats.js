"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@clerk/nextjs";
import {
  listChats,
  createChat,
  updateChatTitle,
  updateChatLanguage,
  deleteChat,
} from "@/lib/api/chats";

export function useChats() {
  const { getToken } = useAuth();
  const queryClient = useQueryClient();

  const chatsQuery = useQuery({
    queryKey: ["chats"],
    queryFn: async () => {
      const token = await getToken();
      return listChats(token);
    },
  });

  const createChatMutation = useMutation({
    mutationFn: async ({ title, output_language }) => {
      const token = await getToken();
      return createChat({ title, output_language }, token);
    },
    onSuccess: (newChat) => {
      queryClient.invalidateQueries({ queryKey: ["chats"] });
      queryClient.setQueryData(["chat", newChat.id], {
        ...newChat,
        messages: [],
      });
    },
  });

  const updateTitleMutation = useMutation({
    mutationFn: async ({ chatId, title }) => {
      const token = await getToken();
      return updateChatTitle(chatId, title, token);
    },
    onMutate: async ({ chatId, title }) => {
      await queryClient.cancelQueries({ queryKey: ["chats"] });
      const previousChats = queryClient.getQueryData(["chats"]);
      if (previousChats) {
        queryClient.setQueryData(
          ["chats"],
          previousChats.map((c) =>
            c.id === chatId ? { ...c, title } : c
          )
        );
      }
      return { previousChats };
    },
    onError: (err, variables, context) => {
      if (context?.previousChats) {
        queryClient.setQueryData(["chats"], context.previousChats);
      }
    },
    onSuccess: (updatedChat) => {
      queryClient.invalidateQueries({ queryKey: ["chats"] });
      queryClient.invalidateQueries({ queryKey: ["chat", updatedChat.id] });
    },
  });

  const updateLanguageMutation = useMutation({
    mutationFn: async ({ chatId, language }) => {
      const token = await getToken();
      return updateChatLanguage(chatId, language, token);
    },
    onMutate: async ({ chatId, language }) => {
      await queryClient.cancelQueries({ queryKey: ["chats"] });
      const previousChats = queryClient.getQueryData(["chats"]);
      if (previousChats) {
        queryClient.setQueryData(
          ["chats"],
          previousChats.map((c) =>
            c.id === chatId ? { ...c, output_language: language } : c
          )
        );
      }
      return { previousChats };
    },
    onError: (err, variables, context) => {
      if (context?.previousChats) {
        queryClient.setQueryData(["chats"], context.previousChats);
      }
    },
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ["chats"] });
      queryClient.invalidateQueries({ queryKey: ["chat", result.chat_id] });
    },
  });

  const deleteChatMutation = useMutation({
    mutationFn: async (chatId) => {
      const token = await getToken();
      return deleteChat(chatId, token);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["chats"] });
    },
  });

  return {
    chats: chatsQuery.data || [],
    isLoading: chatsQuery.isLoading,
    isError: chatsQuery.isError,
    error: chatsQuery.error,
    refetch: chatsQuery.refetch,
    createChat: createChatMutation.mutateAsync,
    isCreating: createChatMutation.isPending,
    updateTitle: updateTitleMutation.mutateAsync,
    isUpdatingTitle: updateTitleMutation.isPending,
    updateLanguage: updateLanguageMutation.mutateAsync,
    isUpdatingLanguage: updateLanguageMutation.isPending,
    deleteChat: deleteChatMutation.mutateAsync,
    isDeleting: deleteChatMutation.isPending,
  };
}

