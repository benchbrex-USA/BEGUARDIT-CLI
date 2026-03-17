// Attack path traversal (§7.4)
// BFS from high-severity entry points.
// Paths with 2+ chained findings escalate composite severity.
import logger from '../logger.js';
import { escalateChain, compareSeverity, SEVERITY_WEIGHT } from '../policy/severity.js';

/**
 * @typedef {Object} AttackPath
 * @property {string} id
 * @property {string} composite_severity
 * @property {number} depth
 * @property {string[]} node_ids — ordered node IDs in the path
 * @property {object[]} steps — { node_id, kind, label, severity? }
 * @property {string[]} edge_relations — relations traversed
 */

/**
 * Find attack paths by BFS from high-severity finding nodes.
 *
 * Only starts traversal from findings with severity >= medium.
 * Paths must contain at least 2 nodes to be interesting.
 *
 * @param {{ nodes: Map, edges: object[], adjacency: Map }} graph
 * @returns {AttackPath[]}
 */
export function findAttackPaths(graph) {
  const { nodes, edges, adjacency } = graph;
  const paths = [];
  let pathCounter = 0;

  // Entry points: finding nodes with severity >= medium
  const entryPoints = [];
  for (const [id, node] of nodes) {
    if (
      node.kind === 'finding' &&
      (SEVERITY_WEIGHT[node.type] || 0) >= SEVERITY_WEIGHT.medium
    ) {
      entryPoints.push(id);
    }
  }

  // Sort entry points by severity (critical first)
  entryPoints.sort((a, b) => {
    const na = nodes.get(a);
    const nb = nodes.get(b);
    return compareSeverity(na.type, nb.type);
  });

  const globalVisited = new Set();

  for (const startId of entryPoints) {
    // BFS from this entry point
    const queue = [[startId]]; // queue of paths (each path = array of node IDs)
    const localVisited = new Set([startId]);

    while (queue.length > 0) {
      const currentPath = queue.shift();
      const currentId = currentPath[currentPath.length - 1];
      const neighbors = adjacency.get(currentId) || [];

      let extended = false;
      for (const nextId of neighbors) {
        if (localVisited.has(nextId)) continue;

        // Only follow chains-to edges between findings, or any edge to assets
        const nextNode = nodes.get(nextId);
        if (!nextNode) continue;

        const edge = edges.find((e) => e.from === currentId && e.to === nextId);
        const relation = edge?.relation || 'unknown';

        // Follow chains-to, exposes, runs-on, authenticates-via, stores-data-in
        const newPath = [...currentPath, nextId];
        localVisited.add(nextId);

        // Cap path depth at 8 to prevent explosion
        if (newPath.length < 8) {
          queue.push(newPath);
        }

        extended = true;

        // Record the path if it has at least 2 nodes and contains a finding
        if (newPath.length >= 2) {
          const findingNodes = newPath
            .map((id) => nodes.get(id))
            .filter((n) => n?.kind === 'finding');

          if (findingNodes.length >= 1) {
            const pathKey = newPath.join('→');
            if (!globalVisited.has(pathKey)) {
              globalVisited.add(pathKey);

              const severities = findingNodes.map((n) => n.type);
              const compositeSeverity = findingNodes.length >= 2
                ? escalateChain(severities)
                : severities[0] || 'info';

              const steps = newPath.map((id) => {
                const n = nodes.get(id);
                return {
                  node_id: id,
                  kind: n.kind,
                  label: n.label,
                  ...(n.kind === 'finding' ? { severity: n.type } : { asset_type: n.type }),
                };
              });

              // Collect edge relations along the path
              const edgeRelations = [];
              for (let i = 0; i < newPath.length - 1; i++) {
                const e = edges.find((e) => e.from === newPath[i] && e.to === newPath[i + 1]);
                edgeRelations.push(e?.relation || 'unknown');
              }

              paths.push({
                id: `path-${++pathCounter}`,
                composite_severity: compositeSeverity,
                depth: newPath.length,
                node_ids: newPath,
                steps,
                edge_relations: edgeRelations,
              });
            }
          }
        }
      }
    }
  }

  // Sort paths: critical first, then by depth descending
  paths.sort((a, b) => {
    const sevCmp = compareSeverity(a.composite_severity, b.composite_severity);
    if (sevCmp !== 0) return sevCmp;
    return b.depth - a.depth;
  });

  // Deduplicate — keep only the longest path starting from each entry point
  const deduped = [];
  const seenEntries = new Set();
  for (const path of paths) {
    const entry = path.node_ids[0];
    const key = `${entry}:${path.composite_severity}`;
    if (!seenEntries.has(key)) {
      seenEntries.add(key);
      deduped.push(path);
    }
  }

  logger.info(
    { totalPaths: paths.length, dedupedPaths: deduped.length, entryPoints: entryPoints.length },
    'attack_paths_found',
  );

  return deduped;
}
