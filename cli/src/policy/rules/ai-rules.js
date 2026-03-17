// Built-in AI / ML security rules (§7.3)
// Each rule: { id, title, category, score, evaluate(evidence) → finding|null }

export default [
  // ── AI Runtimes ────────────────────────────────────────────────────
  {
    id: 'AI-001',
    title: 'Ollama running without authentication',
    category: 'ai-runtimes',
    score: 7.0,
    evaluate(evidence) {
      const e = evidence.find((ev) => ev.type === 'ai_runtimes');
      if (!e) return null;
      const ollama = e.data.runtimes?.find((r) => r.name === 'ollama');
      if (!ollama) return null;
      // Ollama by default has no auth — always flag if detected
      return {
        description: 'Ollama inference server detected. It exposes an unauthenticated API by default.',
        remediation: 'Place Ollama behind a reverse proxy with authentication, or bind to localhost only.',
        metadata: { version: ollama.version },
      };
    },
  },
  {
    id: 'AI-002',
    title: 'GPU with CUDA detected — verify access controls',
    category: 'ai-runtimes',
    score: 4.0,
    evaluate(evidence) {
      const e = evidence.find((ev) => ev.type === 'gpu_info');
      if (!e || e.data.count === 0) return null;
      return {
        description: `${e.data.count} NVIDIA GPU(s) with CUDA available. Verify access is restricted.`,
        remediation: 'Ensure GPU access is limited to authorised users and containers.',
        metadata: { gpus: e.data.gpus },
      };
    },
  },
  {
    id: 'AI-003',
    title: 'ML frameworks installed — supply chain risk',
    category: 'ai-runtimes',
    score: 3.5,
    evaluate(evidence) {
      const e = evidence.find((ev) => ev.type === 'ai_runtimes');
      if (!e) return null;
      const pyMl = e.data.runtimes?.filter((r) => r.type === 'python_ml') || [];
      if (pyMl.length >= 3) {
        return {
          description: `${pyMl.length} ML Python packages installed — increases supply chain surface.`,
          remediation: 'Pin ML dependencies, enable hash verification, use private package mirrors.',
          metadata: { packages: pyMl.map((r) => `${r.name}==${r.version}`) },
        };
      }
      return null;
    },
  },

  // ── AI Models ──────────────────────────────────────────────────────
  {
    id: 'AI-010',
    title: 'Large model files on disk',
    category: 'ai-models',
    score: 4.5,
    evaluate(evidence) {
      const e = evidence.find((ev) => ev.type === 'model_files');
      if (!e || e.data.count === 0) return null;
      const totalGB = e.data.total_size_bytes / (1024 ** 3);
      return {
        description: `${e.data.count} model file(s) found (${totalGB.toFixed(1)} GB total). Model provenance should be verified.`,
        remediation: 'Track model provenance with checksums. Remove unused model files.',
        metadata: { count: e.data.count, total_gb: totalGB.toFixed(1) },
      };
    },
  },
  {
    id: 'AI-011',
    title: 'Pickle-format model files (.bin/.pt/.pth) — deserialization risk',
    category: 'ai-models',
    score: 7.5,
    evaluate(evidence) {
      const e = evidence.find((ev) => ev.type === 'model_files');
      if (!e) return null;
      const pickleModels = e.data.models?.filter((m) => ['bin', 'pt', 'pth'].includes(m.extension)) || [];
      if (pickleModels.length > 0) {
        return {
          description: `${pickleModels.length} model file(s) use pickle-based formats, which are vulnerable to arbitrary code execution on load.`,
          remediation: 'Convert to SafeTensors format. Never load untrusted .bin/.pt files.',
          metadata: { files: pickleModels.map((m) => m.path).slice(0, 10) },
        };
      }
      return null;
    },
  },

  // ── AI Prompts ─────────────────────────────────────────────────────
  {
    id: 'AI-020',
    title: 'System prompt templates in codebase',
    category: 'ai-prompts',
    score: 5.0,
    evaluate(evidence) {
      const e = evidence.find((ev) => ev.type === 'system_prompt_references');
      if (!e || e.data.count === 0) return null;
      return {
        description: `${e.data.count} file(s) reference system prompts — review for prompt injection vectors.`,
        remediation: 'Audit system prompts for injection resistance. Avoid dynamic user input in system prompts.',
        metadata: { files: e.data.files?.slice(0, 10) },
      };
    },
  },
  {
    id: 'AI-021',
    title: 'Prompt template files discovered',
    category: 'ai-prompts',
    score: 3.0,
    evaluate(evidence) {
      const e = evidence.find((ev) => ev.type === 'prompt_template_files');
      if (!e || e.data.count === 0) return null;
      return {
        description: `${e.data.count} prompt template file(s) found. Ensure templates are version-controlled and reviewed.`,
        remediation: 'Store prompt templates in version control with change review.',
        metadata: { count: e.data.count },
      };
    },
  },

  // ── RAG ────────────────────────────────────────────────────────────
  {
    id: 'AI-030',
    title: 'Vector database detected — data exfiltration risk',
    category: 'ai-rag',
    score: 6.0,
    evaluate(evidence) {
      const e = evidence.find((ev) => ev.type === 'vector_databases');
      if (!e || e.data.count === 0) return null;
      return {
        description: `${e.data.count} vector database(s) detected. Embedded data may contain sensitive information.`,
        remediation: 'Apply access controls to vector stores. Audit embedded documents for PII and secrets.',
        metadata: { databases: e.data.databases },
      };
    },
  },
  {
    id: 'AI-031',
    title: 'RAG pipeline libraries installed',
    category: 'ai-rag',
    score: 4.0,
    evaluate(evidence) {
      const e = evidence.find((ev) => ev.type === 'rag_libraries');
      if (!e || e.data.count === 0) return null;
      return {
        description: `${e.data.count} RAG-related library/ies installed. Review retrieval pipeline for data leakage.`,
        remediation: 'Implement retrieval guardrails, document-level access control, and output filtering.',
        metadata: { libraries: e.data.libraries },
      };
    },
  },
  {
    id: 'AI-032',
    title: 'Local vector data stores found',
    category: 'ai-rag',
    score: 5.5,
    evaluate(evidence) {
      const e = evidence.find((ev) => ev.type === 'vector_data_directories');
      if (!e || e.data.count === 0) return null;
      return {
        description: `${e.data.count} local vector data directory/ies found. May contain embedded sensitive documents.`,
        remediation: 'Restrict filesystem permissions on vector stores. Encrypt at rest.',
        metadata: { directories: e.data.directories },
      };
    },
  },
];
