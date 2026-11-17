import { apiFetch } from "./client";

/**
 * Queue or retrieve an existing summary for a video.
 * Returns status 200 (if ready) or 202 (if queued/processing).
 */
export async function requestVideoSummary(videoId, language = "English", token) {
  const query = new URLSearchParams({ language });
  return apiFetch(
    `/api/v1/videos/${videoId}/summarize?${query.toString()}`,
    {
      method: "POST",
    },
    token
  );
}

/**
 * Fetch current summary status and content for a video in a specific language.
 */
export async function getVideoSummary(videoId, language = "English", token) {
  const query = new URLSearchParams({ language });
  return apiFetch(
    `/api/v1/videos/${videoId}/summary?${query.toString()}`,
    {
      method: "GET",
    },
    token
  );
}

/**
 * Download summary PDF as a Blob.
 */
export async function downloadSummaryPdf(videoId, language = "English", token) {
  const query = new URLSearchParams({ language });
  return apiFetch(
    `/api/v1/videos/${videoId}/summary/pdf?${query.toString()}`,
    {
      method: "GET",
    },
    token
  );
}

