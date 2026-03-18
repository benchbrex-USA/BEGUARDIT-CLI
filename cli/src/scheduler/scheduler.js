// Native OS scheduler integration for recurring scans
// Source: ARCH-002-2026-03-17, Section 7.1 (config command), Section 4
//
// Supports:
//   macOS  — launchd plist at ~/Library/LaunchAgents/com.beguardit.scan.plist
//   Linux  — crontab entry
//   Windows — schtasks.exe
import { execSync } from 'node:child_process';
import { existsSync, mkdirSync, readFileSync, writeFileSync, rmSync } from 'node:fs';
import { homedir } from 'node:os';
import { join } from 'node:path';
import logger from '../logger.js';

const PLIST_LABEL = 'com.beguardit.scan';
const PLIST_DIR = join(homedir(), 'Library', 'LaunchAgents');
const PLIST_PATH = join(PLIST_DIR, `${PLIST_LABEL}.plist`);
const CRON_MARKER = '# beguardit-scheduled-scan';
const SCHTASKS_NAME = 'BeGuardit Scan';

/**
 * Resolve the absolute path to the beguardit CLI binary.
 * Prefers the globally installed command; falls back to the local entrypoint.
 */
function resolveBinary() {
  try {
    const which = process.platform === 'win32' ? 'where' : 'which';
    return execSync(`${which} beguardit`, { encoding: 'utf-8' }).trim().split('\n')[0];
  } catch {
    // Fallback: run via node with absolute path to index.js
    const entrypoint = join(import.meta.dirname, '..', 'index.js');
    return `node "${entrypoint}"`;
  }
}

/**
 * Convert a human-readable interval string to minutes.
 * Accepts: "daily", "hourly", "weekly", or a number (minutes).
 */
function intervalMinutes(interval) {
  if (typeof interval === 'number') return interval;
  const map = { hourly: 60, daily: 1440, weekly: 10080 };
  return map[String(interval).toLowerCase()] || 1440;
}

// ────────────────────────────────────────────────────────────────────
//  macOS — launchd
// ────────────────────────────────────────────────────────────────────

function setupLaunchd(binary, minutes, args) {
  const plist = `<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>${PLIST_LABEL}</string>
  <key>ProgramArguments</key>
  <array>
${binary.includes(' ') ? binary.split(' ').map((p) => `    <string>${p}</string>`).join('\n') : `    <string>${binary}</string>`}
    <string>start</string>
${args.map((a) => `    <string>${a}</string>`).join('\n')}
  </array>
  <key>StartInterval</key>
  <integer>${minutes * 60}</integer>
  <key>StandardOutPath</key>
  <string>${join(homedir(), '.beguardit', 'scheduler-stdout.log')}</string>
  <key>StandardErrorPath</key>
  <string>${join(homedir(), '.beguardit', 'scheduler-stderr.log')}</string>
  <key>RunAtLoad</key>
  <false/>
</dict>
</plist>`;

  if (!existsSync(PLIST_DIR)) {
    mkdirSync(PLIST_DIR, { recursive: true });
  }

  // Unload any existing agent first
  if (existsSync(PLIST_PATH)) {
    try {
      execSync(`launchctl unload "${PLIST_PATH}" 2>/dev/null`, { encoding: 'utf-8' });
    } catch { /* may not be loaded */ }
  }

  writeFileSync(PLIST_PATH, plist, 'utf-8');
  execSync(`launchctl load "${PLIST_PATH}"`, { encoding: 'utf-8' });

  logger.info({ path: PLIST_PATH, minutes }, 'launchd_schedule_created');
}

function removeLaunchd() {
  if (!existsSync(PLIST_PATH)) {
    logger.info('launchd_no_agent_found');
    return false;
  }
  try {
    execSync(`launchctl unload "${PLIST_PATH}" 2>/dev/null`, { encoding: 'utf-8' });
  } catch { /* may already be unloaded */ }
  rmSync(PLIST_PATH, { force: true });
  logger.info({ path: PLIST_PATH }, 'launchd_schedule_removed');
  return true;
}

function statusLaunchd() {
  if (!existsSync(PLIST_PATH)) {
    return { scheduled: false, platform: 'launchd' };
  }
  try {
    const content = readFileSync(PLIST_PATH, 'utf-8');
    const intervalMatch = content.match(/<key>StartInterval<\/key>\s*<integer>(\d+)<\/integer>/);
    const intervalSec = intervalMatch ? Number(intervalMatch[1]) : null;
    return {
      scheduled: true,
      platform: 'launchd',
      plistPath: PLIST_PATH,
      intervalMinutes: intervalSec ? intervalSec / 60 : null,
    };
  } catch {
    return { scheduled: false, platform: 'launchd', error: 'could not read plist' };
  }
}

// ────────────────────────────────────────────────────────────────────
//  Linux — crontab
// ────────────────────────────────────────────────────────────────────

function minutesToCronExpr(minutes) {
  if (minutes <= 60) return `*/${minutes} * * * *`;
  if (minutes <= 1440) {
    const hours = Math.round(minutes / 60);
    return `0 */${hours} * * *`;
  }
  // weekly or longer — run Sunday at midnight
  return '0 0 * * 0';
}

function setupCron(binary, minutes, args) {
  const cronExpr = minutesToCronExpr(minutes);
  const command = `${binary} start ${args.join(' ')}`;
  const cronLine = `${cronExpr} ${command} ${CRON_MARKER}`;

  let existing = '';
  try {
    existing = execSync('crontab -l 2>/dev/null', { encoding: 'utf-8' });
  } catch { /* no crontab yet */ }

  // Remove any previous beguardit entries
  const filtered = existing
    .split('\n')
    .filter((line) => !line.includes(CRON_MARKER) && !line.includes('beguardit'))
    .join('\n')
    .replace(/\n{3,}/g, '\n\n');

  const newCrontab = `${filtered.trimEnd()}\n${cronLine}\n`;
  execSync(`echo ${JSON.stringify(newCrontab)} | crontab -`, { encoding: 'utf-8' });

  logger.info({ cronExpr, minutes }, 'cron_schedule_created');
}

function removeCron() {
  let existing;
  try {
    existing = execSync('crontab -l 2>/dev/null', { encoding: 'utf-8' });
  } catch {
    logger.info('cron_no_crontab');
    return false;
  }

  if (!existing.includes('beguardit')) {
    logger.info('cron_no_entry_found');
    return false;
  }

  const filtered = existing
    .split('\n')
    .filter((line) => !line.includes(CRON_MARKER) && !line.includes('beguardit'))
    .join('\n');

  execSync(`echo ${JSON.stringify(filtered)} | crontab -`, { encoding: 'utf-8' });
  logger.info('cron_schedule_removed');
  return true;
}

function statusCron() {
  try {
    const crontab = execSync('crontab -l 2>/dev/null', { encoding: 'utf-8' });
    const entry = crontab.split('\n').find((l) => l.includes(CRON_MARKER) || l.includes('beguardit'));
    if (!entry) return { scheduled: false, platform: 'cron' };
    return { scheduled: true, platform: 'cron', entry: entry.trim() };
  } catch {
    return { scheduled: false, platform: 'cron' };
  }
}

// ────────────────────────────────────────────────────────────────────
//  Windows — schtasks.exe
// ────────────────────────────────────────────────────────────────────

function setupSchtasks(binary, minutes, args) {
  // schtasks requires a modifier; map to closest valid option
  let scheduleType, modifier;
  if (minutes < 1440) {
    scheduleType = 'MINUTE';
    modifier = minutes;
  } else if (minutes < 10080) {
    scheduleType = 'DAILY';
    modifier = Math.max(1, Math.round(minutes / 1440));
  } else {
    scheduleType = 'WEEKLY';
    modifier = 1;
  }

  const command = `${binary} start ${args.join(' ')}`;

  // Remove existing task if present
  try {
    execSync(`schtasks /Delete /TN "${SCHTASKS_NAME}" /F 2>nul`, { encoding: 'utf-8' });
  } catch { /* task may not exist */ }

  execSync(
    `schtasks /Create /TN "${SCHTASKS_NAME}" /TR "${command}" /SC ${scheduleType} /MO ${modifier} /F`,
    { encoding: 'utf-8' },
  );

  logger.info({ scheduleType, modifier, minutes }, 'schtasks_schedule_created');
}

function removeSchtasks() {
  try {
    execSync(`schtasks /Delete /TN "${SCHTASKS_NAME}" /F 2>nul`, { encoding: 'utf-8' });
    logger.info('schtasks_schedule_removed');
    return true;
  } catch {
    logger.info('schtasks_no_task_found');
    return false;
  }
}

function statusSchtasks() {
  try {
    const output = execSync(`schtasks /Query /TN "${SCHTASKS_NAME}" /FO CSV /NH 2>nul`, {
      encoding: 'utf-8',
    });
    if (!output.trim()) return { scheduled: false, platform: 'schtasks' };
    const parts = output.trim().split(',').map((s) => s.replace(/"/g, ''));
    return {
      scheduled: true,
      platform: 'schtasks',
      taskName: parts[0] || SCHTASKS_NAME,
      status: parts[2] || 'unknown',
    };
  } catch {
    return { scheduled: false, platform: 'schtasks' };
  }
}

// ────────────────────────────────────────────────────────────────────
//  Public API
// ────────────────────────────────────────────────────────────────────

/**
 * Register a recurring scan with the OS scheduler.
 *
 * @param {object} config
 * @param {string|number} config.interval — "daily", "hourly", "weekly", or minutes
 * @param {string}  [config.mode]    — scan mode ("offline" | "online")
 * @param {string}  [config.profile] — scan profile ("standard" | "full" | "quick")
 * @param {string[]} [config.categories] — categories to scan
 */
export function setupSchedule(config = {}) {
  const minutes = intervalMinutes(config.interval || 'daily');
  const binary = resolveBinary();

  // Build extra args for the `start` command
  const args = [];
  if (config.mode) args.push('--mode', config.mode);
  if (config.profile) args.push('--profile', config.profile);
  if (config.categories && config.categories.length > 0) {
    args.push('--categories', config.categories.join(','));
  }

  const platform = process.platform;
  logger.info({ platform, minutes, binary }, 'scheduler_setup_start');

  if (platform === 'darwin') {
    setupLaunchd(binary, minutes, args);
  } else if (platform === 'linux') {
    setupCron(binary, minutes, args);
  } else if (platform === 'win32') {
    setupSchtasks(binary, minutes, args);
  } else {
    throw new Error(`Unsupported platform for scheduling: ${platform}`);
  }

  logger.info({ platform, minutes }, 'scheduler_setup_complete');
  return { platform, intervalMinutes: minutes };
}

/**
 * Remove the scheduled scan from the OS scheduler.
 *
 * @returns {boolean} true if a schedule was found and removed
 */
export function removeSchedule() {
  const platform = process.platform;
  logger.info({ platform }, 'scheduler_remove_start');

  if (platform === 'darwin') return removeLaunchd();
  if (platform === 'linux') return removeCron();
  if (platform === 'win32') return removeSchtasks();

  throw new Error(`Unsupported platform for scheduling: ${platform}`);
}

/**
 * Check whether a scheduled scan is currently registered.
 *
 * @returns {{ scheduled: boolean, platform: string, [key: string]: any }}
 */
export function getScheduleStatus() {
  const platform = process.platform;

  if (platform === 'darwin') return statusLaunchd();
  if (platform === 'linux') return statusCron();
  if (platform === 'win32') return statusSchtasks();

  return { scheduled: false, platform: 'unsupported' };
}
