// CLI configuration management
// Source: ARCH-002-2026-03-17, Section 7.1 (config command)
//
// Persists settings to ~/.beguardit/config.json.
// Keys: apiUrl, defaultMode, defaultProfile, outputDir, categories
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { homedir } from 'node:os';
import { join } from 'node:path';

const CONFIG_DIR = join(homedir(), '.beguardit');
const CONFIG_PATH = join(CONFIG_DIR, 'config.json');

const DEFAULTS = {
  apiUrl: 'http://localhost:8000',
  defaultMode: 'offline',
  defaultProfile: 'standard',
  outputDir: join(CONFIG_DIR, 'reports'),
  categories: ['cyber', 'ai'],
};

export function loadConfig() {
  if (!existsSync(CONFIG_PATH)) {
    return { ...DEFAULTS };
  }
  try {
    const raw = readFileSync(CONFIG_PATH, 'utf-8');
    return { ...DEFAULTS, ...JSON.parse(raw) };
  } catch {
    return { ...DEFAULTS };
  }
}

export function saveConfig(config) {
  if (!existsSync(CONFIG_DIR)) {
    mkdirSync(CONFIG_DIR, { recursive: true });
  }
  writeFileSync(CONFIG_PATH, JSON.stringify(config, null, 2) + '\n', 'utf-8');
}

export function getConfigValue(key) {
  const config = loadConfig();
  return config[key];
}

export function setConfigValue(key, value) {
  const config = loadConfig();
  config[key] = value;
  saveConfig(config);
}

export { CONFIG_DIR, CONFIG_PATH, DEFAULTS };
