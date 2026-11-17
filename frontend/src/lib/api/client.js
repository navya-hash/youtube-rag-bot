const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

/**
 * Custom API Error class with status and backend details.
 */
export class ApiError extends Error {
  constructor(message, status = 500, detail = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

/**
 * Centralized fetch helper for communicating with FastAPI backend.
 *
 * @param {string} endpoint - API path (e.g. '/api/v1/chats')
 * @param {object} [options={}] - Standard fetch options
 * @param {string|null} [token=null] - Clerk bearer session token
 * @returns {Promise<any>}
 */
export async function apiFetch(endpoint, options = {}, token = null) {
  const url = `${API_BASE_URL}${endpoint}`;

  const headers = {
    ...options.headers,
  };

  // Only set application/json if body is not FormData or binary
  if (
    options.body &&
    !(options.body instanceof FormData) &&
    !headers["Content-Type"]
  ) {
    headers["Content-Type"] = "application/json";
  }

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  try {
    const response = await fetch(url, {
      ...options,
      headers,
    });

    // Handle PDF or binary responses
    const contentType = response.headers.get("content-type") || "";
    if (contentType.includes("application/pdf")) {
      if (!response.ok) {
        throw new ApiError("Failed to download PDF", response.status);
      }
      return await response.blob();
    }

    // Handle 204 No Content
    if (response.status === 204) {
      return null;
    }

    let data;
    try {
      data = await response.json();
    } catch {
      data = null;
    }

    if (!response.ok) {
      let errorMessage = "An error occurred";
      if (data) {
        if (typeof data.detail === "string") {
          errorMessage = data.detail;
        } else if (data.detail && typeof data.detail === "object") {
          errorMessage = data.detail.message || JSON.stringify(data.detail);
        } else if (data.message) {
          errorMessage = data.message;
        }
      }

      throw new ApiError(errorMessage, response.status, data);
    }

    return data;
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    throw new ApiError(error.message || "Network error", 0);
  }
}

