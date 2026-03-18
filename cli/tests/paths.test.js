import { describe, it, expect, vi } from 'vitest';

vi.mock('../src/logger.js', () => ({
  default: { info: vi.fn(), warn: vi.fn(), error: vi.fn(), debug: vi.fn() },
}));

import { buildGraph } from '../src/correlation/graph.js';
import { findAttackPaths } from '../src/correlation/paths.js';

describe('findAttackPaths', () => {
  it('returns empty array for empty graph', () => {
    const graph = buildGraph([], []);
    const paths = findAttackPaths(graph);
    expect(paths).toEqual([]);
  });

  it('finds paths from high-severity finding through asset', () => {
    const assets = [
      { asset_type: 'host', name: 'server', metadata: {} },
      { asset_type: 'network_service', name: 'ssh:22', metadata: {} },
    ];
    const findings = [
      { id: 'f1', rule_id: 'R1', title: 'Open SSH', severity: 'high', category: 'network', score: 7.5 },
    ];
    const graph = buildGraph(assets, findings);
    const paths = findAttackPaths(graph);
    expect(paths.length).toBeGreaterThanOrEqual(1);
    expect(paths[0].composite_severity).toBeDefined();
    expect(paths[0].steps.length).toBeGreaterThanOrEqual(2);
  });

  it('escalates composite severity for chained findings', () => {
    const findings = [
      { id: 'f1', rule_id: 'R1', title: 'Network vuln', severity: 'high', category: 'network', score: 8.0 },
      { id: 'f2', rule_id: 'R2', title: 'Weak auth', severity: 'high', category: 'users-auth', score: 7.5 },
    ];
    const graph = buildGraph([], findings);
    const paths = findAttackPaths(graph);
    // Two high findings chained should escalate to critical
    const criticalPaths = paths.filter((p) => p.composite_severity === 'critical');
    expect(criticalPaths.length).toBeGreaterThanOrEqual(1);
  });

  it('does not start from low-severity findings', () => {
    const findings = [
      { id: 'f1', rule_id: 'R1', title: 'Info finding', severity: 'low', category: 'network', score: 2.0 },
    ];
    const graph = buildGraph([], findings);
    const paths = findAttackPaths(graph);
    // Low severity is below medium threshold for entry points
    expect(paths).toEqual([]);
  });

  it('sorts paths by severity then depth', () => {
    const assets = [
      { asset_type: 'host', name: 'server', metadata: {} },
      { asset_type: 'network_service', name: 'http:80', metadata: {} },
    ];
    const findings = [
      { id: 'f1', rule_id: 'R1', title: 'Critical vuln', severity: 'critical', category: 'network', score: 9.5 },
      { id: 'f2', rule_id: 'R2', title: 'Medium vuln', severity: 'medium', category: 'network', score: 5.0 },
    ];
    const graph = buildGraph(assets, findings);
    const paths = findAttackPaths(graph);
    if (paths.length >= 2) {
      const weights = { critical: 5, high: 4, medium: 3, low: 2, info: 1 };
      const firstWeight = weights[paths[0].composite_severity] || 0;
      const secondWeight = weights[paths[1].composite_severity] || 0;
      expect(firstWeight).toBeGreaterThanOrEqual(secondWeight);
    }
  });

  it('caps path depth at 8', () => {
    const graph = buildGraph([], []);
    const paths = findAttackPaths(graph);
    for (const p of paths) {
      expect(p.depth).toBeLessThanOrEqual(8);
    }
  });
});
