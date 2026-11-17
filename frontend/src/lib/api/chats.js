import { apiFetch } from "./client";

export const SUPPORTED_LANGUAGES = [
  "English",
  "Hindi",
  "Punjabi",
  "Spanish",
  "French",
  "German",
  "Japanese",
];

export const DEFAULT_LANGUAGE = "English";

/**
 * List all chats for the authenticated user.
 */
export async function listChats(token) {
  return apiFetch("/api/v1/chats", { method: "GET" }, token);
}

/**
 * Create a new chat.
 */
export async function createChat({ title = "New chat", output_language = DEFAULT_LANGUAGE } = {}, token) {
  return apiFetch(
    "/api/v1/chats",
    {
      method: "POST",
      body: JSON.stringify({ title, output_language }),
    },
    token
  );
}

/**
 * Get a specific chat by ID including its messages.
 */
export async function getChat(chatId, token) {
  return apiFetch(`/api/v1/chats/${chatId}`, { method: "GET" }, token);
}

/**
 * Update chat title.
 */
export async function updateChatTitle(chatId, title, token) {
  return apiFetch(
    `/api/v1/chats/${chatId}`,
    {
      method: "PATCH",
      body: JSON.stringify({ title }),
    },
    token
  );
}

/**
 * Update chat output language.
 */
export async function updateChatLanguage(chatId, output_language, token) {
  return apiFetch(
    `/api/v1/chats/${chatId}/language`,
    {
      method: "PATCH",
      body: JSON.stringify({ output_language }),
    },
    token
  );
}

/**
 * Delete a chat.
 */
export async function deleteChat(chatId, token) {
  return apiFetch(
    `/api/v1/chats/${chatId}`,
    {
      method: "DELETE",
    },
    token
  );
}

/**
 * List videos associated with this chat.
 */
export async function listChatVideos(chatId, token) {
  return apiFetch(`/api/v1/chats/${chatId}/videos`, { method: "GET" }, token);
}

/**
 * Disassociate a video from this chat.
 */
export async function removeVideoFromChat(chatId, videoId, token) {
  return apiFetch(
    `/api/v1/chats/${chatId}/videos/${videoId}`,
    {
      method: "DELETE",
    },
    token
  );
}

/**
 * Ask a question using the RAG pipeline.
 */
export async function askQuestion(chatId, question, token) {
  return apiFetch(
    `/api/v1/chats/${chatId}/ask`,
    {
      method: "POST",
      body: JSON.stringify({ question }),
    },
    token
  );
}

/**
 * Append a manual message to a chat.
 */
export async function addMessage(chatId, { role, content }, token) {
  return apiFetch(
    `/api/v1/chats/${chatId}/messages`,
    {
      method: "POST",
      body: JSON.stringify({ role, content }),
    },
    token
  );
}

