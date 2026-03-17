// Policy engine — rule evaluator (§7.3)
// Evaluates collected evidence against the built-in rule library.
// Returns an array of findings, each with:
//   { rule_id, title, description, severity, category, evidence_ids, remediation, metadata }
import { randomUUID } from 'node:crypto';
import logger from '../logger.js';
import { classifySeverity } from './severity.js';
import cyberRules from './rules/cyber-rules.js';
import aiRules from './rules/ai-rules.js';

const ALL_RULES = [...cyberRules, ...aiRules];

/**
 * Evaluate all rules against the collected evidence.
 *
 * @param {object[]} evidence — array of evidence items from collectors
 * @returns {Promise<object[]>} — array of findings
 */
export async function evaluate(evidence) {
  const findings = [];

  for (const rule of ALL_RULES) {
    try {
      const result = rule.evaluate(evidence);
      if (result) {
        // Find evidence IDs that relate to this rule's category
        const relatedEvidence = evidence
          .filter((ev) => ev.collector === rule.category || ev.type?.startsWith(rule.category.replace('-', '_')))
          .map(() => randomUUID()); // Generate placeholder IDs for offline evidence

        findings.push({
          id: randomUUID(),
          rule_id: rule.id,
          title: rule.title,
          description: result.description || '',
          severity: classifySeverity(rule.score),
          score: rule.score,
          category: rule.category,
          evidence_ids: relatedEvidence.slice(0, 5),
          remediation: result.remediation || null,
          metadata: result.metadata || {},
        });

        logger.debug({ ruleId: rule.id, severity: classifySeverity(rule.score) }, 'rule_matched');
      }
    } catch (err) {
      logger.warn({ ruleId: rule.id, error: err.message }, 'rule_evaluation_error');
    }
  }

  // Sort by severity (critical first), then by score descending
  findings.sort((a, b) => b.score - a.score);

  logger.info({ totalRules: ALL_RULES.length, matchedFindings: findings.length }, 'policy_evaluation_complete');
  return findings;
}

/** Expose the rule count for diagnostics. */
export const ruleCount = ALL_RULES.length;
