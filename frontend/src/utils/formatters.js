/**
 * Formatting utilities for display values.
 */

/**
 * Format file size in bytes to human-readable string.
 * @param {number} bytes - File size in bytes.
 * @returns {string} Formatted size string (e.g., "1.5 MB").
 */
export function formatFileSize(bytes) {
  if (bytes === 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB'];
  const k = 1024;
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  const size = parseFloat((bytes / Math.pow(k, i)).toFixed(1));
  return `${size} ${units[i]}`;
}

/**
 * Format a timestamp as a short time string (HH:MM).
 * @param {Date|string|number} timestamp - The timestamp to format.
 * @returns {string} Formatted time string.
 */
export function formatTime(timestamp) {
  const date = new Date(timestamp);
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

/**
 * Truncate a string to a maximum length with ellipsis.
 * @param {string} text - Input string.
 * @param {number} maxLength - Maximum character count.
 * @returns {string} Truncated string.
 */
export function truncate(text, maxLength = 80) {
  if (!text || text.length <= maxLength) return text;
  return text.slice(0, maxLength - 3) + '...';
}

/**
 * Generate a simple unique ID.
 * @returns {string} A unique identifier string.
 */
export function uid() {
  return Date.now().toString(36) + Math.random().toString(36).slice(2, 9);
}

/**
 * Capitalize the first letter of a string.
 * @param {string} str - Input string.
 * @returns {string} Capitalized string.
 */
export function capitalize(str) {
  if (!str) return '';
  return str.charAt(0).toUpperCase() + str.slice(1);
}

/**
 * Convert an agent ID to a display label (e.g., "question_creator" -> "Question Creator").
 * @param {string} agentId - The agent identifier.
 * @returns {string} Human-readable label.
 */
export function agentLabel(agentId) {
  return agentId
    .split('_')
    .map((word) => capitalize(word))
    .join(' ');
}
