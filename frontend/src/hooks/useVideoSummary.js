"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@clerk/nextjs";
import {
  getVideoSummary,
  requestVideoSummary,
  downloadSummaryPdf,
} from "@/lib/api/summary";

export function useVideoSummary(videoId, language = "English") {
  const { getToken } = useAuth();
  const queryClient = useQueryClient();

  const summaryQuery = useQuery({
    queryKey: ["video-summary", videoId, language],
    queryFn: async () => {
      if (!videoId) return null;
      const token = await getToken();
      try {
        return await getVideoSummary(videoId, language, token);
      } catch (err) {
        // If 404, summary hasn't been generated yet
        if (err.status === 404) return null;
        throw err;
      }
    },
    enabled: Boolean(videoId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === "pending" || status === "processing") {
        return 2500; // Poll every 2.5 seconds while worker processes
      }
      return false;
    },
  });

  const requestSummaryMutation = useMutation({
    mutationFn: async ({ targetLanguage = language } = {}) => {
      const token = await getToken();
      return requestVideoSummary(videoId, targetLanguage, token);
    },
    onSuccess: (data, variables) => {
      const targetLang = variables?.targetLanguage || language;
      queryClient.invalidateQueries({
        queryKey: ["video-summary", videoId, targetLang],
      });
    },
  });

  const downloadPdfMutation = useMutation({
    mutationFn: async ({ targetLanguage = language } = {}) => {
      const token = await getToken();
      const blob = await downloadSummaryPdf(videoId, targetLanguage, token);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute(
        "download",
        `video-summary-${videoId}-${targetLanguage.toLowerCase()}.pdf`
      );
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    },
  });

  return {
    summary: summaryQuery.data,
    isLoading: summaryQuery.isLoading,
    isError: summaryQuery.isError,
    error: summaryQuery.error,
    refetch: summaryQuery.refetch,
    requestSummary: requestSummaryMutation.mutateAsync,
    isRequesting: requestSummaryMutation.isPending,
    downloadPdf: downloadPdfMutation.mutateAsync,
    isDownloadingPdf: downloadPdfMutation.isPending,
  };
}

