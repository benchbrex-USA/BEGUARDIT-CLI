// Command: beguardit report
// Source: ARCH-002-2026-03-17, Section 7.1
// Flags: --session <id>, --format json|html
// Re-generates report from saved session data
import { existsSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import logger from '../logger.js';
import { loadConfig } from '../config.js';

export function reportCommand(program) {
  program
    .command('report')
    .description('Re-generate a report from a saved session')
    .requiredOption('-s, --session <id>', 'Session ID to regenerate report for')
    .option('-f, --format <format>', 'Output format: json or html', 'html')
    .action(async (opts) => {
      const config = loadConfig();
      const outputDir = config.outputDir;
      const sessionFile = join(outputDir, `${opts.session}.json`);

      if (!existsSync(sessionFile)) {
        console.error(`\n✗ Session data not found: ${sessionFile}`);
        console.error('  Run "beguardit start" first, or check the session ID.\n');
        process.exit(2);
      }

      console.log(`\n▸ Loading session ${opts.session}...`);
      const reportData = JSON.parse(readFileSync(sessionFile, 'utf-8'));

      logger.info({ sessionId: opts.session, format: opts.format }, 'report_regeneration_started');

      if (opts.format === 'json') {
        const outPath = join(outputDir, `${opts.session}.json`);
        const { generateCanonicalJSON } = await import('../report/json-canonical.js');
        await generateCanonicalJSON(reportData, outPath);
        console.log(`  ✓ JSON report: ${outPath}\n`);
      } else {
        const outPath = join(outputDir, `${opts.session}.html`);
        const { renderHTML } = await import('../report/html-renderer.js');
        await renderHTML(reportData, outPath);
        console.log(`  ✓ HTML report: ${outPath}\n`);
      }

      logger.info({ sessionId: opts.session, format: opts.format }, 'report_regeneration_completed');
    });
}
