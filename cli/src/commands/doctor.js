// Command: beguardit doctor [--verbose]
// Source: ARCH-002-2026-03-17, Section 7.1
// Checks environment prerequisites:
//   - Node version (>= 20)
//   - Disk space
//   - Network connectivity (if online mode)
//   - Write permissions to output directory
//   - Scheduler availability (cron/launchd/Task Scheduler)
import { existsSync, accessSync, constants } from 'node:fs';
import { execSync } from 'node:child_process';
import { homedir } from 'node:os';
import { join } from 'node:path';
import logger from '../logger.js';
import { loadConfig, CONFIG_DIR } from '../config.js';

export function doctorCommand(program) {
  program
    .command('doctor')
    .description('Check environment prerequisites')
    .option('--verbose', 'Show detailed check output')
    .action(async (opts) => {
      console.log('\nBeGuardit Doctor\n');

      const checks = [];

      // 1. Node version
      const nodeVersion = process.versions.node;
      const nodeMajor = parseInt(nodeVersion.split('.')[0], 10);
      checks.push({
        name: 'Node.js version',
        pass: nodeMajor >= 20,
        detail: `v${nodeVersion} ${nodeMajor >= 20 ? '(OK, >= 20)' : '(FAIL: requires >= 20)'}`,
      });

      // 2. Disk space
      try {
        const output = execSync('df -h .', { encoding: 'utf-8' });
        const lines = output.trim().split('\n');
        const available = lines[1]?.split(/\s+/)[3] || 'unknown';
        checks.push({
          name: 'Disk space',
          pass: true,
          detail: `${available} available`,
        });
      } catch {
        checks.push({
          name: 'Disk space',
          pass: false,
          detail: 'Could not determine disk space',
        });
      }

      // 3. Network connectivity (check API reachability)
      const config = loadConfig();
      try {
        const { status } = await fetch(`${config.apiUrl}/api/v1/health`, {
          signal: AbortSignal.timeout(5000),
        });
        checks.push({
          name: 'Network (API)',
          pass: status === 200,
          detail: `${config.apiUrl} — HTTP ${status}`,
        });
      } catch (err) {
        checks.push({
          name: 'Network (API)',
          pass: false,
          detail: `${config.apiUrl} — unreachable (offline mode still works)`,
        });
      }

      // 4. Write permissions
      const outputDir = config.outputDir || join(CONFIG_DIR, 'reports');
      let writable = false;
      try {
        if (existsSync(outputDir)) {
          accessSync(outputDir, constants.W_OK);
          writable = true;
        } else {
          // Check parent is writable
          accessSync(CONFIG_DIR, constants.W_OK);
          writable = true;
        }
      } catch { /* not writable */ }
      checks.push({
        name: 'Write permissions',
        pass: writable,
        detail: writable ? outputDir : `Cannot write to ${outputDir}`,
      });

      // 5. Scheduler availability
      let scheduler = { available: false, name: 'none' };
      const platform = process.platform;
      try {
        if (platform === 'darwin') {
          execSync('which launchctl', { encoding: 'utf-8' });
          scheduler = { available: true, name: 'launchd' };
        } else if (platform === 'linux') {
          execSync('which crontab', { encoding: 'utf-8' });
          scheduler = { available: true, name: 'cron' };
        } else if (platform === 'win32') {
          execSync('where schtasks', { encoding: 'utf-8' });
          scheduler = { available: true, name: 'Task Scheduler' };
        }
      } catch { /* scheduler not found */ }
      checks.push({
        name: 'Scheduler',
        pass: scheduler.available,
        detail: scheduler.available
          ? `${scheduler.name} available`
          : 'No scheduler found (scheduled scans unavailable)',
      });

      // Print results
      let allPassed = true;
      for (const check of checks) {
        const icon = check.pass ? '\x1b[32m✓\x1b[0m' : '\x1b[31m✗\x1b[0m';
        console.log(`  ${icon} ${check.name}: ${check.detail}`);
        if (!check.pass) allPassed = false;

        if (opts.verbose) {
          logger.debug({ check: check.name, pass: check.pass, detail: check.detail });
        }
      }

      console.log('');
      if (allPassed) {
        console.log('All checks passed. Ready to scan.\n');
      } else {
        console.log('Some checks failed. BeGuardit may still work in offline mode.\n');
      }

      process.exit(allPassed ? 0 : 1);
    });
}
