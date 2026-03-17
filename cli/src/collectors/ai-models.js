// AI collector: ai-models (§7.2)
// Inventories: .gguf, .safetensors, .bin, .onnx model files with sizes and hashes
// Profiles: standard, deep
import { createHash } from 'node:crypto';
import { createReadStream, existsSync, statSync } from 'node:fs';
import { homedir } from 'node:os';
import { join } from 'node:path';
import BaseCollector from './base.js';

export default class AiModelsCollector extends BaseCollector {
  constructor() {
    super();
    this.name = 'ai-models';
    this.category = 'ai';
    this.platforms = ['linux', 'darwin', 'win32'];
    this.profiles = ['standard', 'deep'];
  }

  async collect(context) {
    const evidence = [];
    const assets = [];

    const modelExtensions = ['gguf', 'safetensors', 'bin', 'onnx', 'pt', 'pth', 'h5', 'pb', 'tflite', 'mlmodel'];
    const extGlob = modelExtensions.map((e) => `-name "*.${e}"`).join(' -o ');

    // ── Search common model directories ─────────────────────────────
    const searchPaths = [
      join(homedir(), '.cache', 'huggingface'),
      join(homedir(), '.ollama', 'models'),
      join(homedir(), '.cache', 'torch'),
      join(homedir(), '.cache', 'lm-studio'),
      join(homedir(), 'models'),
      '/opt/models',
      '/var/lib/ollama',
    ];

    // Also do a broader search in deep mode
    if (context.profile === 'deep') {
      searchPaths.push(join(homedir(), '.local', 'share'));
      searchPaths.push('/srv');
    }

    const allModels = [];

    for (const searchPath of searchPaths) {
      if (!existsSync(searchPath)) continue;

      const found = this.exec(
        `find "${searchPath}" -maxdepth 5 \\( ${extGlob} \\) -type f 2>/dev/null | head -100`,
      );
      if (!found) continue;

      for (const filePath of found.split('\n').filter(Boolean)) {
        try {
          const stat = statSync(filePath);
          const ext = filePath.split('.').pop();
          const model = {
            path: filePath,
            extension: ext,
            size_bytes: stat.size,
            size_human: this._humanSize(stat.size),
            modified_at: stat.mtime.toISOString(),
          };

          // Compute SHA-256 for files under 1 GB (skip large models for speed)
          if (stat.size < 1_073_741_824 && context.profile === 'deep') {
            model.sha256 = await this._hashFile(filePath);
          }

          allModels.push(model);
          assets.push(this.asset('ai_model', filePath, {
            extension: ext,
            size_bytes: stat.size,
          }));
        } catch { /* stat failed */ }
      }
    }

    evidence.push(this.evidence('model_files', {
      models: allModels,
      count: allModels.length,
      total_size_bytes: allModels.reduce((sum, m) => sum + m.size_bytes, 0),
    }));

    // ── Hugging Face cache metadata ─────────────────────────────────
    const hfCache = join(homedir(), '.cache', 'huggingface', 'hub');
    if (existsSync(hfCache)) {
      const repos = this.exec(`ls -d "${hfCache}"/models--* 2>/dev/null`);
      if (repos) {
        const hfModels = repos.split('\n').filter(Boolean).map((dir) => {
          const name = dir.split('models--').pop()?.replace(/--/g, '/');
          return { repo_id: name, local_path: dir };
        });
        evidence.push(this.evidence('huggingface_cache', {
          models: hfModels,
          count: hfModels.length,
        }));
      }
    }

    return { evidence, assets };
  }

  _humanSize(bytes) {
    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    let i = 0;
    let size = bytes;
    while (size >= 1024 && i < units.length - 1) { size /= 1024; i++; }
    return `${size.toFixed(1)} ${units[i]}`;
  }

  _hashFile(filePath) {
    return new Promise((resolve, reject) => {
      const hash = createHash('sha256');
      const stream = createReadStream(filePath);
      stream.on('data', (chunk) => hash.update(chunk));
      stream.on('end', () => resolve(hash.digest('hex')));
      stream.on('error', () => resolve(null));
    });
  }
}
