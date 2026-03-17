// JSON canonical output — machine-readable, tamper-evident format (§7.5)
// Schema version: 1.0
//
// Structure:
//   { version, session_id, hostname, os_info, scan_config,
//     started_at, completed_at, summary, assets, findings,
//     evidence, attack_paths, integrity }
//
// The integrity field contains a SHA-256 hash of the report body
// (everything except the integrity field itself) for tamper detection.
import { createHash } from 'node:crypto';
import { writeFileSync } from 'node:fs';
import logger from '../logger.js';

/**
 * Generate the canonical JSON report file.
 *
 * @param {object} reportData — assembled by start.js
 * @param {string} outPath   — file path to write
 */
export async function generateCanonicalJSON(reportData, outPath) {
  const report = {
    schema_version: '1.0',
    session_id: reportData.session_id,
    generated_at: new Date().toISOString(),

    // ── Host context ─────────────────────────────────────────────────
    hostname: reportData.hostname,
    os_info: reportData.os_info || {},

    // ── Scan configuration ───────────────────────────────────────────
    scan_config: reportData.scan_config,
    started_at: reportData.started_at,
    completed_at: reportData.completed_at,

    // ── Summary ──────────────────────────────────────────────────────
    summary: {
      total_findings: reportData.summary?.total || 0,
      by_severity: {
        critical: reportData.summary?.critical || 0,
        high: reportData.summary?.high || 0,
        medium: reportData.summary?.medium || 0,
        low: reportData.summary?.low || 0,
        info: reportData.summary?.info || 0,
      },
      total_assets: reportData.assets?.length || 0,
      total_evidence: reportData.evidence?.length || 0,
      total_attack_paths: reportData.attack_paths?.length || 0,
    },

    // ── Assets ───────────────────────────────────────────────────────
    assets: (reportData.assets || []).map((a, i) => ({
      index: i,
      asset_type: a.asset_type,
      name: a.name,
      metadata: a.metadata || {},
    })),

    // ── Findings ─────────────────────────────────────────────────────
    findings: (reportData.findings || []).map((f) => ({
      id: f.id,
      rule_id: f.rule_id,
      title: f.title,
      description: f.description,
      severity: f.severity,
      score: f.score,
      category: f.category,
      evidence_ids: f.evidence_ids || [],
      remediation: f.remediation,
      metadata: f.metadata || {},
    })),

    // ── Evidence ─────────────────────────────────────────────────────
    evidence: (reportData.evidence || []).map((e, i) => ({
      index: i,
      collector: e.collector,
      type: e.type,
      data: e.data,
      collected_at: e.collected_at,
    })),

    // ── Attack paths ─────────────────────────────────────────────────
    attack_paths: (reportData.attack_paths || []).map((p) => ({
      id: p.id,
      composite_severity: p.composite_severity,
      depth: p.depth,
      steps: p.steps,
      edge_relations: p.edge_relations,
    })),
  };

  // ── Integrity hash ─────────────────────────────────────────────────
  // SHA-256 of the stringified report body (deterministic key order)
  const bodyString = JSON.stringify(report, null, 2);
  const hash = createHash('sha256').update(bodyString).digest('hex');

  const output = {
    ...report,
    integrity: {
      algorithm: 'sha256',
      hash,
    },
  };

  writeFileSync(outPath, JSON.stringify(output, null, 2) + '\n', 'utf-8');
  logger.info({ path: outPath, hash }, 'canonical_json_written');
}
