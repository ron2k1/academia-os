/**
 * REST API client for the AcademiaOS backend.
 */
import axios from 'axios';
import { API_BASE } from '../utils/constants';

const client = axios.create({
  baseURL: API_BASE,
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
});

/**
 * Fetch backend health status.
 * @returns {Promise<object>} Health status object.
 */
export async function fetchHealth() {
  const { data } = await client.get('/health');
  return data;
}

/**
 * Fetch classes configuration.
 * @returns {Promise<object>} Classes config with semester and classes array.
 */
export async function fetchClasses() {
  const { data } = await client.get('/classes');
  return data;
}

/**
 * Fetch progress tracker data.
 * @returns {Promise<object>} Progress data.
 */
export async function fetchProgress() {
  const { data } = await client.get('/progress');
  return data;
}

/**
 * Upload a file to a class category.
 * @param {string} classId - Target class.
 * @param {string} category - Upload category (textbooks, practice, submissions, rubrics).
 * @param {File} file - The file to upload.
 * @param {function} [onProgress] - Progress callback (0-100).
 * @returns {Promise<object>} Upload result.
 */
export async function uploadFile(classId, category, file, onProgress) {
  const formData = new FormData();
  formData.append('file', file);

  const { data } = await client.post(
    `/upload/${classId}/${category}`,
    formData,
    {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (e) => {
        if (onProgress && e.total) {
          onProgress(Math.round((e.loaded / e.total) * 100));
        }
      },
    }
  );
  return data;
}

/**
 * List files in a class category.
 * @param {string} classId - The class ID.
 * @param {string} category - File category.
 * @returns {Promise<Array<object>>} Array of file info objects.
 */
export async function listFiles(classId, category) {
  const { data } = await client.get(`/files/${classId}/${category}`);
  return data.files || [];
}

/**
 * Read a vault file.
 * @param {string} classId - The class ID.
 * @param {string} path - Relative file path.
 * @returns {Promise<object>} File content data.
 */
export async function readVault(classId, path) {
  const { data } = await client.get(`/vault/${classId}/${path}`);
  return data;
}

export default client;
