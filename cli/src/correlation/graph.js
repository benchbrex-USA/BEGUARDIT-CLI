// Correlation graph builder (§7.4)
// Builds a directed graph where:
//   Nodes: assets (hosts, services, AI runtimes, models) and findings
//   Edges: runs-on, exposes, authenticates-via, stores-data-in, chains-to
//
// The graph is represented as adjacency lists for efficient BFS traversal.
import logger from '../logger.js';

/**
 * @typedef {Object} GraphNode
 * @property {string} id
 * @property {'asset'|'finding'} kind
 * @property {string} type — asset_type or severity
 * @property {string} label — display name
 * @property {object} data — full record
 */

/**
 * @typedef {Object} GraphEdge
 * @property {string} from
 * @property {string} to
 * @property {string} relation
 */

/**
 * Build a correlation graph from assets and findings.
 *
 * @param {object[]} assets   — { asset_type, name, metadata }
 * @param {object[]} findings — { id, rule_id, title, severity, category, ... }
 * @returns {{ nodes: Map<string, GraphNode>, edges: GraphEdge[], adjacency: Map<string, string[]> }}
 */
export function buildGraph(assets, findings) {
  const nodes = new Map();
  const edges = [];
  const adjacency = new Map();

  const addNode = (node) => {
    nodes.set(node.id, node);
    if (!adjacency.has(node.id)) adjacency.set(node.id, []);
  };

  const addEdge = (from, to, relation) => {
    edges.push({ from, to, relation });
    if (!adjacency.has(from)) adjacency.set(from, []);
    adjacency.get(from).push(to);
  };

  // ── Asset nodes ────────────────────────────────────────────────────
  const assetNodes = [];
  for (let i = 0; i < assets.length; i++) {
    const a = assets[i];
    const id = `asset:${i}:${a.asset_type}:${a.name}`;
    const node = { id, kind: 'asset', type: a.asset_type, label: a.name, data: a };
    addNode(node);
    assetNodes.push(node);
  }

  // ── Finding nodes ──────────────────────────────────────────────────
  const findingNodes = [];
  for (const f of findings) {
    const id = `finding:${f.id}`;
    const node = { id, kind: 'finding', type: f.severity, label: f.title, data: f };
    addNode(node);
    findingNodes.push(node);
  }

  // ── Build edges ────────────────────────────────────────────────────
  // Host node (anchor for the system)
  const hostNode = assetNodes.find((n) => n.type === 'host');

  for (const an of assetNodes) {
    // Services, packages, runtimes run ON the host
    if (hostNode && an.id !== hostNode.id) {
      const serviceTypes = ['network_service', 'service', 'package_manager', 'ai_runtime', 'gpu'];
      if (serviceTypes.includes(an.type)) {
        addEdge(an.id, hostNode.id, 'runs-on');
      }
    }

    // AI models stored in the filesystem
    if (an.type === 'ai_model') {
      if (hostNode) addEdge(an.id, hostNode.id, 'stores-data-in');
    }

    // Vector databases store data
    if (an.type === 'vector_database' || an.type === 'vector_data_store') {
      if (hostNode) addEdge(an.id, hostNode.id, 'stores-data-in');
    }

    // Prompt stores relate to AI runtimes
    if (an.type === 'prompt_store' || an.type === 'prompt_template') {
      const runtime = assetNodes.find((n) => n.type === 'ai_runtime');
      if (runtime) addEdge(an.id, runtime.id, 'configures');
    }

    // User accounts authenticate via SSH keys
    if (an.type === 'user_account') {
      if (hostNode) addEdge(an.id, hostNode.id, 'authenticates-via');
    }
  }

  // ── Link findings to related assets by category ────────────────────
  const categoryToAssetType = {
    'users-auth': ['user_account'],
    'network': ['network_service'],
    'filesystem': ['suid_binary'],
    'ai-runtimes': ['ai_runtime', 'gpu'],
    'ai-models': ['ai_model'],
    'ai-prompts': ['prompt_store', 'prompt_template'],
    'ai-rag': ['vector_database', 'vector_data_store'],
    'packages': ['package_manager'],
    'services': ['service'],
  };

  for (const fn of findingNodes) {
    const f = fn.data;
    const relatedTypes = categoryToAssetType[f.category] || [];

    // Link finding → related assets via "exposes"
    for (const an of assetNodes) {
      if (relatedTypes.includes(an.type)) {
        addEdge(fn.id, an.id, 'exposes');
      }
    }

    // Chain findings in the same category together
    for (const other of findingNodes) {
      if (other.id !== fn.id && other.data.category === f.category) {
        // Higher-severity finding chains to lower-severity
        if ((f.score || 0) > (other.data.score || 0)) {
          addEdge(fn.id, other.id, 'chains-to');
        }
      }
    }
  }

  // ── Cross-category chaining ────────────────────────────────────────
  // If there's a network finding AND a users-auth finding, they chain
  const crossChains = [
    ['network', 'users-auth'],
    ['ai-runtimes', 'ai-models'],
    ['ai-prompts', 'ai-rag'],
    ['network', 'ai-runtimes'],
    ['users-auth', 'filesystem'],
  ];

  for (const [catA, catB] of crossChains) {
    const aFindings = findingNodes.filter((n) => n.data.category === catA);
    const bFindings = findingNodes.filter((n) => n.data.category === catB);
    for (const a of aFindings) {
      for (const b of bFindings) {
        addEdge(a.id, b.id, 'chains-to');
      }
    }
  }

  logger.info(
    { nodeCount: nodes.size, edgeCount: edges.length },
    'correlation_graph_built',
  );

  return { nodes, edges, adjacency };
}
