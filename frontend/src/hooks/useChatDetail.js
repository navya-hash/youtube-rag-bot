"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@clerk/nextjs";
import { getChat, askQuestion } from "@/lib/api/chats";

export function useChatDetail(chatId) {
  const { getToken } = useAuth();
  const queryClient = useQueryClient();

  const chatQuery = useQuery({
    queryKey: ["chat", chatId],
    queryFn: async () => {
      if (!chatId) return null;
      const token = await getToken();
      return getChat(chatId, token);
    },
    enabled: Boolean(chatId),
  });

  const askMutation = useMutation({
    mutationFn: async ({ question }) => {
      const token = await getToken();
      return askQuestion(chatId, question, token);
    },
    onMutate: async ({ question }) => {
      // Optimistically append the user message to the UI
      await queryClient.cancelQueries({ queryKey: ["chat", chatId] });
      const previousChat = queryClient.getQueryData(["chat", chatId]);

      if (previousChat) {
        const optimisticUserMessage = {
          id: `temp-${Date.now()}`,
          role: "user",
          content: question,
          citations: null,
          created_at: new Date().toISOString(),
        };

        queryClient.setQueryData(["chat", chatId], {
          ...previousChat,
          messages: [...(previousChat.messages || []), optimisticUserMessage],
        });
      }

      return { previousChat };
    },
    onError: (err, variables, context) => {
      if (context?.previousChat) {
        queryClient.setQueryData(["chat", chatId], context.previousChat);
      }
    },
    onSuccess: (ragResponse) => {
      // Replace with full server state or append assistant answer
      queryClient.setQueryData(["chat", chatId], (old) => {
        if (!old) return old;

        // Clean out optimistic temp message and append authoritative question + answer
        const filtered = (old.messages || []).filter(
          (m) => !m.id.startsWith("temp-")
        );

        const newQuestionMsg = {
          id: ragResponse.question.id,
          role: "user",
          content: ragResponse.question.content,
          citations: null,
          created_at: new Date().toISOString(),
        };

        const newAnswerMsg = {
          id: ragResponse.answer.id,
          role: "assistant",
          content: ragResponse.answer.content,
          citations: ragResponse.citations || [],
          output_language: ragResponse.output_language,
          created_at: new Date().toISOString(),
        };

        return {
          ...old,
          messages: [...filtered, newQuestionMsg, newAnswerMsg],
        };
      });
      queryClient.invalidateQueries({ queryKey: ["chats"] });
    },
  });

  return {
    chat: chatQuery.data,
    isLoading: chatQuery.isLoading,
    isError: chatQuery.isError,
    error: chatQuery.error,
    refetch: chatQuery.refetch,
    askQuestion: askMutation.mutateAsync,
    isAsking: askMutation.isPending,
    askError: askMutation.error,
  };
}

