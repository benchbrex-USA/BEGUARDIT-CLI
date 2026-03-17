// Severity classification logic (§7.3)
// Levels: critical (9.0-10.0), high (7.0-8.9), medium (4.0-6.9), low (0.1-3.9), info (0.0)
//
// Follows CVSS v3.1 qualitative rating scale.

/**
 * Map a numeric score (0–10) to a severity label.
 * @param {number} score
 * @returns {'critical'|'high'|'medium'|'low'|'info'}
 */
export function classifySeverity(score) {
  if (score >= 9.0) return 'critical';
  if (score >= 7.0) return 'high';
  if (score >= 4.0) return 'medium';
  if (score >= 0.1) return 'low';
  return 'info';
}

/** Numeric weight for severity ordering. */
export const SEVERITY_WEIGHT = {
  critical: 5,
  high: 4,
  medium: 3,
  low: 2,
  info: 1,
};

/**
 * Compare two severity labels (for sorting, higher first).
 * @param {string} a
 * @param {string} b
 * @returns {number}
 */
export function compareSeverity(a, b) {
  return (SEVERITY_WEIGHT[b] || 0) - (SEVERITY_WEIGHT[a] || 0);
}

/**
 * Escalate composite severity for chained findings (§7.4).
 * Two medium findings in a chain → high; two high → critical.
 * @param {string[]} severities — array of severity labels in the chain
 * @returns {string}
 */
export function escalateChain(severities) {
  const maxWeight = Math.max(...severities.map((s) => SEVERITY_WEIGHT[s] || 0));
  const count = severities.length;

  if (count >= 2 && maxWeight >= SEVERITY_WEIGHT.high) return 'critical';
  if (count >= 2 && maxWeight >= SEVERITY_WEIGHT.medium) return 'high';
  if (count >= 3 && maxWeight >= SEVERITY_WEIGHT.low) return 'medium';

  // Fallback to the max individual severity
  return Object.entries(SEVERITY_WEIGHT).find(([, w]) => w === maxWeight)?.[0] || 'info';
}
