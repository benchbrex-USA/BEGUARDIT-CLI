// Command: beguardit start
// Source: ARCH-002-2026-03-17, Section 7.1
// Flags: --mode offline|online, --profile quick|standard|deep, --categories <list>, --output <dir>
// Flow: collect -> evaluate -> correlate -> report
// If flags are omitted, uses Inquirer.js guided prompts.
import { randomUUID } from 'node:crypto';
import { existsSync, mkdirSync } from 'node:fs';
import { join } from 'node:path';
import inquirer from 'inquirer';
import logger from '../logger.js';
import { loadConfig } from '../config.js';

// Exit codes per §17.3: 0 = success, 1 = partial failure, 2 = fatal error
const EXIT_SUCCESS = 0;
const EXIT_PARTIAL = 1;
const EXIT_FATAL = 2;

export function startCommand(program) {
  program
    .command('start')
    .description('Run a security assessment')
    .option('-m, --mode <mode>', 'Assessment mode: offline or online', undefined)
    .option('-p, --profile <profile>', 'Scan profile: quick, standard, or deep', undefined)
    .option('-c, --categories <categories>', 'Comma-separated collector categories (cyber,ai)', undefined)
    .option('-o, --output <dir>', 'Output directory for reports', undefined)
    .action(async (opts) => {
      const config = loadConfig();

      // ── Interactive prompts if flags omitted ──────────────────────
      if (!opts.mode) {
        const answer = await inquirer.prompt([{
          type: 'list',
          name: 'mode',
          message: 'Assessment mode:',
          choices: [
            { name: 'Offline — collect & report locally', value: 'offline' },
            { name: 'Online  — upload results to API', value: 'online' },
          ],
          default: config.defaultMode,
        }]);
        opts.mode = answer.mode;
      }

      if (!opts.profile) {
        const answer = await inquirer.prompt([{
          type: 'list',
          name: 'profile',
          message: 'Scan profile:',
          choices: [
            { name: 'Quick    — fast sweep, critical checks only', value: 'quick' },
            { name: 'Standard — balanced coverage (recommended)', value: 'standard' },
            { name: 'Deep     — thorough, all collectors', value: 'deep' },
          ],
          default: config.defaultProfile,
        }]);
        opts.profile = answer.profile;
      }

      if (!opts.categories) {
        const answer = await inquirer.prompt([{
          type: 'checkbox',
          name: 'categories',
          message: 'Collector categories:',
          choices: [
            { name: 'Cyber security', value: 'cyber', checked: true },
            { name: 'AI / ML posture', value: 'ai', checked: true },
          ],
        }]);
        opts.categories = answer.categories.join(',');
      }

      const outputDir = opts.output || config.outputDir;
      const categories = opts.categories.split(',').map((c) => c.trim());
      const sessionId = randomUUID();

      // Ensure output directory exists
      if (!existsSync(outputDir)) {
        mkdirSync(outputDir, { recursive: true });
      }

      console.log('\n┌─────────────────────────────────────────┐');
      console.log('│        BeGuardit Assessment Start        │');
      console.log('├─────────────────────────────────────────┤');
      console.log(`│  Session:    ${sessionId}  │`);
      console.log(`│  Mode:       ${opts.mode.padEnd(28)}│`);
      console.log(`│  Profile:    ${opts.profile.padEnd(28)}│`);
      console.log(`│  Categories: ${categories.join(', ').padEnd(28)}│`);
      console.log('└─────────────────────────────────────────┘\n');

      logger.info({ sessionId, mode: opts.mode, profile: opts.profile, categories }, 'assessment_started');

      let exitCode = EXIT_SUCCESS;

      try {
        // Step 1: Collect evidence
        console.log('▸ Collecting evidence...');
        const { runCollectors } = await import('../collectors/index.js');
        const { evidence, assets, collectorErrors } = await runCollectors({
          sessionId,
          profile: opts.profile,
          categories,
        });
        if (collectorErrors.length > 0) {
          exitCode = EXIT_PARTIAL;
          for (const err of collectorErrors) {
            logger.warn({ collector: err.collector, error: err.message }, 'collector_failed');
            console.log(`  ⚠ ${err.collector}: ${err.message}`);
          }
        }
        console.log(`  ✓ ${evidence.length} evidence items from ${assets.length} assets\n`);

        // Step 2: Evaluate policies
        console.log('▸ Evaluating policies...');
        const { evaluate } = await import('../policy/engine.js');
        const findings = await evaluate(evidence);
        const summary = {
          total: findings.length,
          critical: findings.filter((f) => f.severity === 'critical').length,
          high: findings.filter((f) => f.severity === 'high').length,
          medium: findings.filter((f) => f.severity === 'medium').length,
          low: findings.filter((f) => f.severity === 'low').length,
          info: findings.filter((f) => f.severity === 'info').length,
        };
        console.log(`  ✓ ${summary.total} findings (${summary.critical} critical, ${summary.high} high, ${summary.medium} medium)\n`);

        // Step 3: Correlate attack paths
        console.log('▸ Building correlation graph...');
        const { buildGraph } = await import('../correlation/graph.js');
        const { findAttackPaths } = await import('../correlation/paths.js');
        const graph = buildGraph(assets, findings);
        const attackPaths = findAttackPaths(graph);
        console.log(`  ✓ ${attackPaths.length} attack paths identified\n`);

        // Step 4: Generate reports
        console.log('▸ Generating reports...');
        const { generateCanonicalJSON } = await import('../report/json-canonical.js');
        const { renderHTML } = await import('../report/html-renderer.js');

        const reportData = {
          version: '1.0',
          session_id: sessionId,
          hostname: (await import('node:os')).hostname(),
          os_info: {},
          scan_config: { mode: opts.mode, profile: opts.profile, categories },
          started_at: new Date().toISOString(),
          completed_at: new Date().toISOString(),
          summary,
          assets,
          findings,
          evidence,
          attack_paths: attackPaths,
        };

        const jsonPath = join(outputDir, `${sessionId}.json`);
        const htmlPath = join(outputDir, `${sessionId}.html`);
        await generateCanonicalJSON(reportData, jsonPath);
        await renderHTML(reportData, htmlPath);
        console.log(`  ✓ JSON report: ${jsonPath}`);
        console.log(`  ✓ HTML report: ${htmlPath}\n`);

        // Step 5: Upload (online mode)
        if (opts.mode === 'online') {
          console.log('▸ Uploading to API...');
          const { uploadAssessment } = await import('../upload/client.js');
          await uploadAssessment(jsonPath, config.apiUrl);
          console.log('  ✓ Uploaded successfully\n');
        }

        logger.info({ sessionId, summary, exitCode }, 'assessment_completed');
        console.log('Assessment complete.\n');
      } catch (err) {
        logger.error({ sessionId, error: err.message }, 'assessment_fatal_error');
        console.error(`\n✗ Fatal error: ${err.message}\n`);
        exitCode = EXIT_FATAL;
      }

      process.exit(exitCode);
    });
}
