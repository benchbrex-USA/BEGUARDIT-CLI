import { describe, it, expect, vi } from 'vitest';

// Mock the logger to avoid pino initialization issues in tests
vi.mock('../src/logger.js', () => ({
  default: { info: vi.fn(), warn: vi.fn(), error: vi.fn(), debug: vi.fn() },
}));

import { buildGraph } from '../src/correlation/graph.js';

describe('buildGraph', () => {
  it('returns empty graph when no assets or findings', () => {
    const graph = buildGraph([], []);
    expect(graph.nodes.size).toBe(0);
    expect(graph.edges).toHaveLength(0);
  });

  it('creates asset nodes', () => {
    const assets = [
      { asset_type: 'host', name: 'server-1', metadata: {} },
      { asset_type: 'network_service', name: 'nginx:443', metadata: {} },
    ];
    const graph = buildGraph(assets, []);
    expect(graph.nodes.size).toBe(2);

    const nodeKinds = [...graph.nodes.values()].map((n) => n.kind);
    expect(nodeKinds).toEqual(['asset', 'asset']);
  });

  it('creates finding nodes', () => {
    const findings = [
      { id: 'f1', rule_id: 'R1', title: 'Open SSH', severity: 'high', category: 'network', score: 7.5 },
    ];
    const graph = buildGraph([], findings);
    expect(graph.nodes.size).toBe(1);
    expect(graph.nodes.get('finding:f1').kind).toBe('finding');
  });

  it('adds runs-on edges for services to host', () => {
    const assets = [
      { asset_type: 'host', name: 'server-1', metadata: {} },
      { asset_type: 'network_service', name: 'nginx:443', metadata: {} },
    ];
    const graph = buildGraph(assets, []);
    const runsOnEdges = graph.edges.filter((e) => e.relation === 'runs-on');
    expect(runsOnEdges.length).toBeGreaterThanOrEqual(1);
  });

  it('links findings to related assets via exposes', () => {
    const assets = [
      { asset_type: 'host', name: 'server-1', metadata: {} },
      { asset_type: 'network_service', name: 'nginx:443', metadata: {} },
    ];
    const findings = [
      { id: 'f1', rule_id: 'R1', title: 'Open port', severity: 'medium', category: 'network', score: 5.0 },
    ];
    const graph = buildGraph(assets, findings);
    const exposesEdges = graph.edges.filter((e) => e.relation === 'exposes');
    expect(exposesEdges.length).toBeGreaterThanOrEqual(1);
  });

  it('chains findings in the same category by score', () => {
    const findings = [
      { id: 'f1', rule_id: 'R1', title: 'High network', severity: 'high', category: 'network', score: 8.0 },
      { id: 'f2', rule_id: 'R2', title: 'Med network', severity: 'medium', category: 'network', score: 5.0 },
    ];
    const graph = buildGraph([], findings);
    const chainsTo = graph.edges.filter((e) => e.relation === 'chains-to');
    expect(chainsTo.length).toBeGreaterThanOrEqual(1);
    // Higher-score finding chains to lower
    expect(chainsTo.some((e) => e.from === 'finding:f1' && e.to === 'finding:f2')).toBe(true);
  });

  it('adds cross-category chains', () => {
    const findings = [
      { id: 'f1', rule_id: 'R1', title: 'Network vuln', severity: 'high', category: 'network', score: 7.0 },
      { id: 'f2', rule_id: 'R2', title: 'Weak auth', severity: 'medium', category: 'users-auth', score: 5.0 },
    ];
    const graph = buildGraph([], findings);
    const crossChains = graph.edges.filter(
      (e) => e.relation === 'chains-to' && e.from === 'finding:f1' && e.to === 'finding:f2'
    );
    expect(crossChains.length).toBeGreaterThanOrEqual(1);
  });

  it('populates adjacency map', () => {
    const assets = [{ asset_type: 'host', name: 'srv', metadata: {} }];
    const findings = [{ id: 'f1', rule_id: 'R1', title: 'Test', severity: 'low', category: 'network', score: 2.0 }];
    const graph = buildGraph(assets, findings);
    expect(graph.adjacency.size).toBeGreaterThan(0);
  });
});
