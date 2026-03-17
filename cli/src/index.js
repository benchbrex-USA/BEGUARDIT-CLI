#!/usr/bin/env node
// BeGuardit CLI — entry point
// Source: ARCH-002-2026-03-17, Section 7.1
//
// Commands: version, doctor, start, report, upload, config, uninstall
// Framework: Commander.js 12.x + Inquirer.js 9.x
import { Command } from 'commander';
import { createRequire } from 'node:module';

import { versionCommand } from './commands/version.js';
import { doctorCommand } from './commands/doctor.js';
import { startCommand } from './commands/start.js';
import { reportCommand } from './commands/report.js';
import { uploadCommand } from './commands/upload.js';
import { configCommand } from './commands/config.js';
import { uninstallCommand } from './commands/uninstall.js';

const require = createRequire(import.meta.url);
const pkg = require('../package.json');

const program = new Command();

program
  .name('beguardit')
  .description('Terminal-first cybersecurity and AI security assessment tool')
  .version(pkg.version, '-v, --version', 'Print CLI version');

// ── Commands ──────────────────────────────────────────────────────────────

versionCommand(program);
doctorCommand(program);
startCommand(program);
reportCommand(program);
uploadCommand(program);
configCommand(program);
uninstallCommand(program);

// ── Parse ─────────────────────────────────────────────────────────────────

program.parse(process.argv);

// Show help if no command provided
if (!process.argv.slice(2).length) {
  program.help();
}
