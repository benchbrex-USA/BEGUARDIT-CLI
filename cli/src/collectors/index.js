// Collector registry and runner (§7.2)
// Loads all collectors, filters by platform + selected profile/categories,
// and runs them in parallel. Returns { evidence, assets, collectorErrors }.
import logger from '../logger.js';

// ── Collector imports ───────────────────────────────────────────────
import OsInfoCollector from './os-info.js';
import NetworkCollector from './network.js';
import ServicesCollector from './services.js';
import PackagesCollector from './packages.js';
import UsersAuthCollector from './users-auth.js';
import FilesystemCollector from './filesystem.js';
import AiRuntimesCollector from './ai-runtimes.js';
import AiModelsCollector from './ai-models.js';
import AiPromptsCollector from './ai-prompts.js';
import AiRagCollector from './ai-rag.js';

// ── Registry ────────────────────────────────────────────────────────
const ALL_COLLECTORS = [
  // Cyber (6)
  new OsInfoCollector(),
  new NetworkCollector(),
  new ServicesCollector(),
  new PackagesCollector(),
  new UsersAuthCollector(),
  new FilesystemCollector(),
  // AI (4)
  new AiRuntimesCollector(),
  new AiModelsCollector(),
  new AiPromptsCollector(),
  new AiRagCollector(),
];

/**
 * Run all applicable collectors and aggregate results.
 *
 * @param {object} opts
 * @param {string} opts.sessionId
 * @param {string} opts.profile   — 'quick' | 'standard' | 'deep'
 * @param {string[]} opts.categories — e.g. ['cyber', 'ai']
 * @returns {Promise<{ evidence: object[], assets: object[], collectorErrors: object[] }>}
 */
export async function runCollectors({ sessionId, profile, categories }) {
  // Filter collectors by platform, profile, and selected categories
  const applicable = ALL_COLLECTORS.filter((c) =>
    c.isSupported() &&
    c.matchesProfile(profile) &&
    categories.includes(c.category),
  );

  logger.info(
    { sessionId, profile, categories, total: ALL_COLLECTORS.length, applicable: applicable.length },
    'collectors_filtered',
  );

  const evidence = [];
  const assets = [];
  const collectorErrors = [];

  // Run all applicable collectors concurrently
  const results = await Promise.allSettled(
    applicable.map(async (collector) => {
      const start = Date.now();
      logger.debug({ collector: collector.name }, 'collector_started');

      const result = await collector.collect({ sessionId, profile });

      const durationMs = Date.now() - start;
      logger.info(
        { collector: collector.name, evidence: result.evidence.length, assets: result.assets.length, durationMs },
        'collector_completed',
      );

      return { name: collector.name, ...result };
    }),
  );

  for (const result of results) {
    if (result.status === 'fulfilled') {
      evidence.push(...result.value.evidence);
      assets.push(...result.value.assets);
    } else {
      // Extract collector name from the error or the settled promise
      const errorMessage = result.reason?.message || String(result.reason);
      const collectorName = result.reason?.collectorName || 'unknown';
      collectorErrors.push({ collector: collectorName, message: errorMessage });
      logger.error({ collector: collectorName, error: errorMessage }, 'collector_error');
    }
  }

  logger.info(
    { sessionId, evidenceCount: evidence.length, assetCount: assets.length, errorCount: collectorErrors.length },
    'collection_complete',
  );

  return { evidence, assets, collectorErrors };
}
