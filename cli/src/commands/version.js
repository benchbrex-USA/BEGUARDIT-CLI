// Command: beguardit version
// Source: ARCH-002-2026-03-17, Section 7.1
// Prints CLI version, build hash, Node version
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const pkg = require('../../package.json');

export function versionCommand(program) {
  program
    .command('version')
    .description('Print CLI version, build hash, and Node version')
    .action(() => {
      const buildHash = process.env.BUILD_HASH || 'dev';
      const nodeVersion = process.version;

      console.log(`beguardit v${pkg.version}`);
      console.log(`  Build:  ${buildHash}`);
      console.log(`  Node:   ${nodeVersion}`);
      console.log(`  OS:     ${process.platform} ${process.arch}`);
    });
}
