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
      let evidence = [];
      let assets = [];
      let findings = [];
      let attackPaths = [];
      let summary = {};
      let reportData = null;

      // Remediation hints per step
      const HINTS = {
        collect: [
          'Check that collectors have required permissions (e.g., sudo for network scans)',
          'Try a different scan profile (--profile quick) to skip failing collectors',
          'Run "beguardit doctor" to verify system prerequisites',
        ],
        evaluate: [
          'This may indicate corrupted evidence data — try re-collecting',
          'Try re-running the assessment with --profile standard',
        ],
        correlate: [
          'Correlation requires at least one finding and one asset',
          'Try running with more collector categories (--categories cyber,ai)',
        ],
        report: [
          'Check disk space and write permissions on the output directory',
          'Try specifying a different output directory with --output <dir>',
        ],
        upload: [
          'Verify API connectivity: check your network and API URL in config',
          'Run "beguardit config show" to verify your API endpoint',
          'The assessment was saved locally — you can upload later with "beguardit upload <file>"',
        ],
      };

      function handleStepError(step, err) {
        exitCode = EXIT_PARTIAL;
        logger.error({ sessionId, step, error: err.message }, `${step}_failed`);
        console.log(`  ✗ ${step} failed: ${err.message}`);
        for (const hint of HINTS[step] || []) {
          console.log(`    Hint: ${hint}`);
        }
        console.log('');
      }

      // Step 1: Collect evidence
      try {
        console.log('▸ Collecting evidence...');
        const { runCollectors } = await import('../collectors/index.js');
        const result = await runCollectors({
          sessionId,
          profile: opts.profile,
          categories,
        });
        evidence = result.evidence;
        assets = result.assets;
        if (result.collectorErrors.length > 0) {
          exitCode = EXIT_PARTIAL;
          for (const err of result.collectorErrors) {
            logger.warn({ collector: err.collector, error: err.message }, 'collector_failed');
            console.log(`  ⚠ ${err.collector}: ${err.message}`);
          }
        }
        console.log(`  ✓ ${evidence.length} evidence items from ${assets.length} assets\n`);
      } catch (err) {
        handleStepError('collect', err);
        process.exit(EXIT_FATAL);
      }

      // Step 2: Evaluate policies
      try {
        console.log('▸ Evaluating policies...');
        const { evaluate } = await import('../policy/engine.js');
        findings = await evaluate(evidence);
        summary = {
          total: findings.length,
          critical: findings.filter((f) => f.severity === 'critical').length,
          high: findings.filter((f) => f.severity === 'high').length,
          medium: findings.filter((f) => f.severity === 'medium').length,
          low: findings.filter((f) => f.severity === 'low').length,
          info: findings.filter((f) => f.severity === 'info').length,
        };
        console.log(`  ✓ ${summary.total} findings (${summary.critical} critical, ${summary.high} high, ${summary.medium} medium)\n`);
      } catch (err) {
        handleStepError('evaluate', err);
      }

      // Step 3: Correlate attack paths
      try {
        console.log('▸ Building correlation graph...');
        const { buildGraph } = await import('../correlation/graph.js');
        const { findAttackPaths } = await import('../correlation/paths.js');
        const graph = buildGraph(assets, findings);
        attackPaths = findAttackPaths(graph);
        console.log(`  ✓ ${attackPaths.length} attack paths identified\n`);
      } catch (err) {
        handleStepError('correlate', err);
      }

      // Step 4: Generate reports
      try {
        console.log('▸ Generating reports...');
        const { generateCanonicalJSON } = await import('../report/json-canonical.js');
        const { renderHTML } = await import('../report/html-renderer.js');

        reportData = {
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
        if (opts.mode === 'online' && reportData) {
          try {
            const { validateReport } = await import('../validation/report-schema.js');
            const validation = validateReport(reportData);
            if (!validation.valid) {
              console.log('  ⚠ Report validation failed:');
              for (const verr of validation.errors) {
                console.log(`    • ${verr}`);
              }
              logger.warn({ errors: validation.errors }, 'report_validation_failed');
              exitCode = EXIT_PARTIAL;
            } else {
              console.log('▸ Uploading to API...');
              const { uploadAssessment } = await import('../upload/client.js');
              await uploadAssessment(jsonPath, config.apiUrl);
              console.log('  ✓ Uploaded successfully\n');
            }
          } catch (err) {
            handleStepError('upload', err);
          }
        }
      } catch (err) {
        handleStepError('report', err);
      }

      logger.info({ sessionId, summary, exitCode }, 'assessment_completed');
      console.log('Assessment complete.\n');

      process.exit(exitCode);
    });
}
