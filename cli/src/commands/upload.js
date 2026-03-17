// Command: beguardit upload
// Source: ARCH-002-2026-03-17, Section 7.1
// Flags: --session <id>, --api-url <url>, --token <token>
// Uploads offline session data to the API backend
import { existsSync } from 'node:fs';
import { join } from 'node:path';
import logger from '../logger.js';
import { loadConfig } from '../config.js';

export function uploadCommand(program) {
  program
    .command('upload')
    .description('Upload an offline session to the API')
    .requiredOption('-s, --session <id>', 'Session ID to upload')
    .option('-a, --api-url <url>', 'API base URL (overrides config)')
    .option('-t, --token <token>', 'Authentication token')
    .action(async (opts) => {
      const config = loadConfig();
      const apiUrl = opts.apiUrl || config.apiUrl;
      const sessionFile = join(config.outputDir, `${opts.session}.json`);

      if (!existsSync(sessionFile)) {
        console.error(`\n✗ Session data not found: ${sessionFile}`);
        console.error('  Run "beguardit start" first, or check the session ID.\n');
        process.exit(2);
      }

      if (!opts.token) {
        console.error('\n✗ Authentication token required. Use --token <token>.\n');
        process.exit(2);
      }

      console.log(`\n▸ Uploading session ${opts.session} to ${apiUrl}...`);
      logger.info({ sessionId: opts.session, apiUrl }, 'upload_started');

      // Retry with exponential backoff (§17.3: 3 retries)
      const MAX_RETRIES = 3;
      let lastError;

      for (let attempt = 1; attempt <= MAX_RETRIES; attempt++) {
        try {
          const { uploadAssessment } = await import('../upload/client.js');
          const result = await uploadAssessment(sessionFile, apiUrl, opts.token);
          console.log(`  ✓ Uploaded successfully (server session: ${result.session_id})\n`);
          logger.info({ sessionId: opts.session, attempt }, 'upload_completed');
          return;
        } catch (err) {
          lastError = err;
          logger.warn({ sessionId: opts.session, attempt, error: err.message }, 'upload_retry');
          if (attempt < MAX_RETRIES) {
            const delay = Math.pow(2, attempt) * 1000; // 2s, 4s
            console.log(`  ⚠ Attempt ${attempt} failed. Retrying in ${delay / 1000}s...`);
            await new Promise((resolve) => setTimeout(resolve, delay));
          }
        }
      }

      console.error(`\n✗ Upload failed after ${MAX_RETRIES} attempts: ${lastError.message}\n`);
      logger.error({ sessionId: opts.session, error: lastError.message }, 'upload_failed');
      process.exit(2);
    });
}
