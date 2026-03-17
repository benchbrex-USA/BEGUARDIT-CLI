// Command: beguardit uninstall [--confirm]
// Source: ARCH-002-2026-03-17, Section 7.1
// Removes CLI, scheduled tasks, and local data
import { existsSync, rmSync } from 'node:fs';
import { execSync } from 'node:child_process';
import inquirer from 'inquirer';
import logger from '../logger.js';
import { CONFIG_DIR } from '../config.js';

export function uninstallCommand(program) {
  program
    .command('uninstall')
    .description('Remove CLI, scheduled tasks, and local data')
    .option('--confirm', 'Skip confirmation prompt')
    .action(async (opts) => {
      console.log('\nBeGuardit Uninstall\n');
      console.log('This will remove:');
      console.log(`  • Configuration and data: ${CONFIG_DIR}`);
      console.log('  • Scheduled scan tasks (launchd/cron/schtasks)');
      console.log('  • Global npm package: beguardit\n');

      if (!opts.confirm) {
        const answer = await inquirer.prompt([{
          type: 'confirm',
          name: 'proceed',
          message: 'Are you sure you want to uninstall BeGuardit?',
          default: false,
        }]);
        if (!answer.proceed) {
          console.log('\nUninstall cancelled.\n');
          return;
        }
      }

      // 1. Remove scheduled tasks
      console.log('▸ Removing scheduled tasks...');
      const platform = process.platform;
      try {
        if (platform === 'darwin') {
          const plistPath = `${process.env.HOME}/Library/LaunchAgents/com.beguardit.scan.plist`;
          if (existsSync(plistPath)) {
            execSync(`launchctl unload "${plistPath}" 2>/dev/null || true`, { encoding: 'utf-8' });
            rmSync(plistPath, { force: true });
            console.log('  ✓ Removed launchd agent');
          } else {
            console.log('  – No launchd agent found');
          }
        } else if (platform === 'linux') {
          try {
            const crontab = execSync('crontab -l 2>/dev/null', { encoding: 'utf-8' });
            if (crontab.includes('beguardit')) {
              const filtered = crontab
                .split('\n')
                .filter((line) => !line.includes('beguardit'))
                .join('\n');
              execSync(`echo "${filtered}" | crontab -`, { encoding: 'utf-8' });
              console.log('  ✓ Removed cron entries');
            } else {
              console.log('  – No cron entries found');
            }
          } catch {
            console.log('  – No crontab configured');
          }
        } else if (platform === 'win32') {
          try {
            execSync('schtasks /Delete /TN "BeGuardit Scan" /F 2>nul', { encoding: 'utf-8' });
            console.log('  ✓ Removed scheduled task');
          } catch {
            console.log('  – No scheduled task found');
          }
        }
      } catch (err) {
        console.log(`  ⚠ Could not remove scheduled tasks: ${err.message}`);
      }

      // 2. Remove config directory and data
      console.log('▸ Removing configuration and data...');
      if (existsSync(CONFIG_DIR)) {
        rmSync(CONFIG_DIR, { recursive: true, force: true });
        console.log(`  ✓ Removed ${CONFIG_DIR}`);
      } else {
        console.log('  – No configuration directory found');
      }

      // 3. Uninstall global npm package
      console.log('▸ Removing global package...');
      try {
        execSync('npm uninstall -g beguardit 2>/dev/null', { encoding: 'utf-8' });
        console.log('  ✓ Removed global npm package');
      } catch {
        console.log('  – Package not installed globally (or using local install)');
      }

      logger.info('uninstall_completed');
      console.log('\nBeGuardit has been uninstalled.\n');
    });
}
