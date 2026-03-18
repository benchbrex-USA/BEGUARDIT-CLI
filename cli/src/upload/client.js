// Upload client — sends assessment reports to the BeGuardit API
// Source: ARCH-002-2026-03-17, Section 7.1 (upload command)
import { readFileSync } from 'node:fs';
import { basename } from 'node:path';
import logger from '../logger.js';

/**
 * Upload a canonical JSON assessment report to the API backend.
 *
 * @param {string} filePath — path to the JSON report file
 * @param {string} apiUrl   — API base URL (e.g. http://localhost:8000)
 * @param {string} token    — Bearer authentication token
 * @returns {Promise<{ session_id: string }>} server-assigned session identifier
 */
export async function uploadAssessment(filePath, apiUrl, token) {
  const fileName = basename(filePath);
  const fileContents = readFileSync(filePath, 'utf-8');

  // Validate that the file is valid JSON before sending
  let parsed;
  try {
    parsed = JSON.parse(fileContents);
  } catch (err) {
    throw new Error(`Invalid JSON in report file ${fileName}: ${err.message}`);
  }

  const sessionId = parsed.session_id || fileName.replace(/\.json$/, '');
  logger.debug({ fileName, sessionId, apiUrl }, 'upload_preparing');

  // Build multipart form body using the standard FormData API (Node 18+)
  const blob = new Blob([fileContents], { type: 'application/json' });
  const form = new FormData();
  form.append('file', blob, fileName);

  const endpoint = `${apiUrl.replace(/\/+$/, '')}/api/v1/upload/assessment`;

  logger.debug({ endpoint }, 'upload_sending');

  const response = await fetch(endpoint, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: 'application/json',
    },
    body: form,
  });

  if (!response.ok) {
    let detail = '';
    try {
      const body = await response.json();
      detail = body.detail || body.message || JSON.stringify(body);
    } catch {
      detail = await response.text().catch(() => '');
    }
    throw new Error(
      `Upload failed (HTTP ${response.status}): ${detail || response.statusText}`,
    );
  }

  const result = await response.json();

  if (!result.session_id) {
    throw new Error('Server response missing session_id');
  }

  logger.info({ sessionId: result.session_id }, 'upload_success');
  return { session_id: result.session_id };
}
