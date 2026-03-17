// AI collector: ai-rag (§7.2)
// Detects: vector databases (ChromaDB, Qdrant, Weaviate, Pinecone, Milvus),
//          embeddings config, RAG pipeline code
// Profiles: standard, deep
import { existsSync } from 'node:fs';
import { homedir } from 'node:os';
import { join } from 'node:path';
import BaseCollector from './base.js';

export default class AiRagCollector extends BaseCollector {
  constructor() {
    super();
    this.name = 'ai-rag';
    this.category = 'ai';
    this.platforms = ['linux', 'darwin', 'win32'];
    this.profiles = ['standard', 'deep'];
  }

  async collect(context) {
    const evidence = [];
    const assets = [];

    // ── Vector database processes / services ────────────────────────
    const vectorDbs = [
      { process: 'chroma', name: 'ChromaDB', defaultPort: 8000 },
      { process: 'qdrant', name: 'Qdrant', defaultPort: 6333 },
      { process: 'weaviate', name: 'Weaviate', defaultPort: 8080 },
      { process: 'milvus', name: 'Milvus', defaultPort: 19530 },
    ];

    const detectedDbs = [];
    for (const db of vectorDbs) {
      const running = this.exec(
        process.platform === 'win32'
          ? `tasklist /FI "IMAGENAME eq ${db.process}*" 2>nul`
          : `pgrep -la "${db.process}" 2>/dev/null`,
      );
      if (running && !running.includes('INFO: No tasks')) {
        detectedDbs.push({
          name: db.name,
          process_match: db.process,
          default_port: db.defaultPort,
          running: true,
        });
        assets.push(this.asset('vector_database', db.name, { port: db.defaultPort }));
      }
    }

    // Docker containers running vector DBs
    const dockerVecDbs = this.exec('docker ps --format "{{.Names}}\t{{.Image}}" 2>/dev/null');
    if (dockerVecDbs) {
      const keywords = ['chroma', 'qdrant', 'weaviate', 'milvus', 'pinecone', 'pgvector'];
      for (const line of dockerVecDbs.split('\n').filter(Boolean)) {
        const [name, image] = line.split('\t');
        const match = keywords.find((kw) => image?.toLowerCase().includes(kw));
        if (match) {
          detectedDbs.push({
            name: `${match} (docker: ${name})`,
            image,
            running: true,
            source: 'docker',
          });
          assets.push(this.asset('vector_database', `docker:${name}`, { image }));
        }
      }
    }

    evidence.push(this.evidence('vector_databases', {
      databases: detectedDbs,
      count: detectedDbs.length,
    }));

    // ── Python RAG libraries ────────────────────────────────────────
    const pip = this.exec('pip3 list --format=json 2>/dev/null') || this.exec('pip list --format=json 2>/dev/null');
    const ragLibraries = [];
    if (pip) {
      try {
        const packages = JSON.parse(pip);
        const ragPackages = {
          chromadb: 'ChromaDB Client',
          'qdrant-client': 'Qdrant Client',
          'weaviate-client': 'Weaviate Client',
          pinecone: 'Pinecone Client',
          'pinecone-client': 'Pinecone Client',
          pymilvus: 'Milvus Client',
          pgvector: 'pgvector',
          faiss: 'FAISS',
          'faiss-cpu': 'FAISS CPU',
          'faiss-gpu': 'FAISS GPU',
          'sentence-transformers': 'Sentence Transformers',
          'langchain-community': 'LangChain Community',
          'llama-index': 'LlamaIndex',
          'llama-index-core': 'LlamaIndex Core',
          unstructured: 'Unstructured',
          'langchain-openai': 'LangChain OpenAI',
          'langchain-anthropic': 'LangChain Anthropic',
        };

        for (const pkg of packages) {
          const label = ragPackages[pkg.name.toLowerCase()];
          if (label) {
            ragLibraries.push({ name: pkg.name, version: pkg.version, label });
          }
        }
      } catch { /* malformed JSON */ }
    }
    evidence.push(this.evidence('rag_libraries', {
      libraries: ragLibraries,
      count: ragLibraries.length,
    }));

    // ── Embeddings & vector store config files ──────────────────────
    const searchRoots = [process.cwd(), join(homedir(), 'projects'), join(homedir(), 'code')];
    const configPatterns = [
      'chroma_config', 'qdrant_config', 'vector_store', 'vectorstore',
      'embeddings', 'embedding_model', 'OPENAI_API_KEY', 'PINECONE_API_KEY',
    ];
    const patternArgs = configPatterns.map((p) => `-e "${p}"`).join(' ');
    const configFiles = [];

    for (const root of searchRoots) {
      if (!existsSync(root)) continue;
      const found = this.exec(
        `grep -rl ${patternArgs} "${root}" --include="*.py" --include="*.yaml" --include="*.yml" --include="*.toml" --include="*.env" 2>/dev/null | head -30`,
      );
      if (found) {
        for (const filePath of found.split('\n').filter(Boolean)) {
          configFiles.push({ path: filePath });
        }
      }
    }
    evidence.push(this.evidence('rag_config_files', {
      files: configFiles,
      count: configFiles.length,
    }));

    // ── ChromaDB / FAISS local data directories ─────────────────────
    const dataDirNames = ['chroma_data', 'chromadb', '.chroma', 'faiss_index', 'vector_store', 'vectordb'];
    const dataDirs = [];

    for (const root of searchRoots) {
      if (!existsSync(root)) continue;
      for (const dirName of dataDirNames) {
        const found = this.exec(
          `find "${root}" -maxdepth 4 -type d -name "${dirName}" 2>/dev/null | head -10`,
        );
        if (found) {
          for (const dir of found.split('\n').filter(Boolean)) {
            dataDirs.push({ path: dir, name: dirName });
            assets.push(this.asset('vector_data_store', dir, { type: dirName }));
          }
        }
      }
    }
    evidence.push(this.evidence('vector_data_directories', {
      directories: dataDirs,
      count: dataDirs.length,
    }));

    return { evidence, assets };
  }
}
