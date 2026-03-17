// BaseCollector abstract class — Strategy pattern (§7.2)
// All collectors extend this and implement collect()
//
// Evidence item shape:
//   { collector, type, data, collected_at }
//
// Asset shape:
//   { asset_type, name, metadata }
import { execSync } from 'node:child_process';
import logger from '../logger.js';

export default class BaseCollector {
  constructor() {
    this.name = '';            // unique collector identifier (e.g. 'os-info')
    this.category = '';        // 'cyber' | 'ai'
    this.platforms = [];       // ['linux', 'darwin', 'win32']
    this.profiles = ['quick', 'standard', 'deep']; // profiles that include this collector
  }

  /**
   * Run the collector and return evidence + assets.
   * Subclasses MUST override this.
   * @param {object} context - { sessionId, profile }
   * @returns {Promise<{ evidence: object[], assets: object[] }>}
   */
  async collect(context) {
    throw new Error(`${this.constructor.name}.collect() not implemented`);
  }

  /** Check whether this collector can run on the current platform. */
  isSupported() {
    return this.platforms.includes(process.platform);
  }

  /** Check whether this collector is included in the selected profile. */
  matchesProfile(profile) {
    return this.profiles.includes(profile);
  }

  // ---------------------------------------------------------------------------
  // Helpers available to all collectors
  // ---------------------------------------------------------------------------

  /**
   * Run a shell command and return stdout, or null on failure.
   * @param {string} cmd
   * @param {object} [opts]
   * @returns {string|null}
   */
  exec(cmd, opts = {}) {
    try {
      return execSync(cmd, { encoding: 'utf-8', timeout: 30_000, ...opts }).trim();
    } catch (err) {
      logger.debug({ collector: this.name, cmd, error: err.message }, 'exec_failed');
      return null;
    }
  }

  /** Build an evidence item with standard fields. */
  evidence(type, data) {
    return {
      collector: this.name,
      type,
      data,
      collected_at: new Date().toISOString(),
    };
  }

  /** Build an asset record. */
  asset(assetType, name, metadata = {}) {
    return {
      asset_type: assetType,
      name,
      metadata,
    };
  }
}
