// Command: beguardit config
// Source: ARCH-002-2026-03-17, Section 7.1
// Flags: --set <key=value>, --get <key>, --list
// Manages CLI configuration (API URL, default mode, etc.)
import { loadConfig, saveConfig, CONFIG_PATH, DEFAULTS } from '../config.js';

export function configCommand(program) {
  program
    .command('config')
    .description('Manage CLI configuration')
    .option('--set <key=value>', 'Set a configuration value (e.g. apiUrl=https://api.example.com)')
    .option('--get <key>', 'Get a configuration value')
    .option('--list', 'List all configuration values')
    .action((opts) => {
      const config = loadConfig();

      if (opts.set) {
        const eqIndex = opts.set.indexOf('=');
        if (eqIndex === -1) {
          console.error('\n✗ Invalid format. Use --set key=value\n');
          process.exit(2);
        }
        const key = opts.set.slice(0, eqIndex);
        const value = opts.set.slice(eqIndex + 1);

        if (!(key in DEFAULTS)) {
          console.error(`\n✗ Unknown config key: "${key}"`);
          console.error(`  Valid keys: ${Object.keys(DEFAULTS).join(', ')}\n`);
          process.exit(2);
        }

        // Preserve type: arrays stay arrays
        let parsed = value;
        if (Array.isArray(DEFAULTS[key])) {
          parsed = value.split(',').map((v) => v.trim());
        }

        config[key] = parsed;
        saveConfig(config);
        console.log(`\n  ✓ ${key} = ${JSON.stringify(parsed)}`);
        console.log(`  Saved to ${CONFIG_PATH}\n`);
        return;
      }

      if (opts.get) {
        if (!(opts.get in config)) {
          console.error(`\n✗ Unknown config key: "${opts.get}"`);
          console.error(`  Valid keys: ${Object.keys(DEFAULTS).join(', ')}\n`);
          process.exit(2);
        }
        console.log(`\n  ${opts.get} = ${JSON.stringify(config[opts.get])}\n`);
        return;
      }

      // Default: --list or no flags → show all
      console.log(`\nBeGuardit Configuration (${CONFIG_PATH})\n`);
      for (const [key, value] of Object.entries(config)) {
        const isDefault = JSON.stringify(value) === JSON.stringify(DEFAULTS[key]);
        const tag = isDefault ? ' (default)' : '';
        console.log(`  ${key} = ${JSON.stringify(value)}${tag}`);
      }
      console.log('');
    });
}
