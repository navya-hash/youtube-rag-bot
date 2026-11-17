import { apiFetch } from "./client";

/**
 * Ingest a YouTube video transcript for a specific chat.
 *
 * @param {object} payload
 * @param {string} payload.url - YouTube URL
 * @param {string} payload.chat_id - UUID of the chat
 * @param {string} [payload.language="en"] - Transcript language preference
 * @param {string} token - Clerk session token
 */
export async function ingestVideo({ url, chat_id, language = "en" }, token) {
  return apiFetch(
    "/api/v1/youtube/ingest",
    {
      method: "POST",
      body: JSON.stringify({ url, chat_id, language }),
    },
    token
  );
}

