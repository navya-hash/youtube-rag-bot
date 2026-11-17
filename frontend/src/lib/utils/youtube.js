/**
 * Extracts YouTube video ID from various YouTube URL formats:
 * - https://www.youtube.com/watch?v=VIDEO_ID
 * - https://m.youtube.com/watch?v=VIDEO_ID
 * - https://youtu.be/VIDEO_ID
 * - https://www.youtube.com/shorts/VIDEO_ID
 * - https://www.youtube.com/embed/VIDEO_ID
 *
 * @param {string} url - YouTube video URL
 * @returns {string|null} - 11-character YouTube video ID or null
 */
export function extractYouTubeVideoId(url) {
  if (!url || typeof url !== "string") return null;

  const trimmed = url.trim();

  // Pattern covering standard watch, shorts, embed, and short youtu.be URLs
  const patterns = [
    /(?:youtu\.be\/|youtube\.com\/(?:embed\/|v\/|shorts\/|watch\?v=|watch\?.+&v=))([\w-]{11})/,
    /^([\w-]{11})$/, // If already an 11-char ID
  ];

  for (const pattern of patterns) {
    const match = trimmed.match(pattern);
    if (match && match[1]) {
      return match[1];
    }
  }

  return null;
}

/**
 * Validates if a string is a valid YouTube URL or video ID.
 * @param {string} url
 * @returns {boolean}
 */
export function isValidYouTubeUrl(url) {
  return extractYouTubeVideoId(url) !== null;
}

/**
 * Returns thumbnail URLs for a YouTube video ID.
 * @param {string} videoId
 * @returns {{ default: string, medium: string, high: string, maxres: string }}
 */
export function getYouTubeThumbnails(videoId) {
  if (!videoId) {
    return {
      default: "/hero.png",
      medium: "/hero.png",
      high: "/hero.png",
      maxres: "/hero.png",
    };
  }

  return {
    default: `https://img.youtube.com/vi/${videoId}/default.jpg`,
    medium: `https://img.youtube.com/vi/${videoId}/mqdefault.jpg`,
    high: `https://img.youtube.com/vi/${videoId}/hqdefault.jpg`,
    maxres: `https://img.youtube.com/vi/${videoId}/maxresdefault.jpg`,
  };
}

/**
 * Generates a YouTube watch URL with timestamp.
 * @param {string} videoId
 * @param {number} [startSeconds=0]
 * @returns {string}
 */
export function getYouTubeTimestampUrl(videoId, startSeconds = 0) {
  if (!videoId) return "#";
  const sec = Math.max(0, Math.floor(Number(startSeconds) || 0));
  return `https://www.youtube.com/watch?v=${videoId}&t=${sec}s`;
}

