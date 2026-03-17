// AI collector: ai-runtimes (§7.2)
// Detects: Python ML environments, Ollama, vLLM, TGI, ONNX Runtime, TensorRT
// Profiles: quick, standard, deep
import BaseCollector from './base.js';

export default class AiRuntimesCollector extends BaseCollector {
  constructor() {
    super();
    this.name = 'ai-runtimes';
    this.category = 'ai';
    this.platforms = ['linux', 'darwin', 'win32'];
    this.profiles = ['quick', 'standard', 'deep'];
  }

  async collect(context) {
    const evidence = [];
    const assets = [];
    const runtimes = [];

    // ── Ollama ──────────────────────────────────────────────────────
    const ollamaVersion = this.exec('ollama --version 2>/dev/null');
    if (ollamaVersion) {
      const version = ollamaVersion.match(/(\d+\.\d+\.\d+)/)?.[1] || ollamaVersion;
      runtimes.push({ name: 'ollama', version, type: 'inference_server' });
      assets.push(this.asset('ai_runtime', 'ollama', { version }));

      // List served models
      const models = this.exec('ollama list 2>/dev/null');
      if (models) {
        const modelList = models.split('\n').slice(1).filter(Boolean).map((line) => {
          const parts = line.split(/\s+/);
          return { name: parts[0], id: parts[1], size: parts[2] };
        });
        evidence.push(this.evidence('ollama_models', { models: modelList, count: modelList.length }));
      }
    }

    // ── Python ML frameworks ────────────────────────────────────────
    const pip = this.exec('pip3 list --format=json 2>/dev/null') || this.exec('pip list --format=json 2>/dev/null');
    if (pip) {
      try {
        const packages = JSON.parse(pip);
        const mlPackages = {
          torch: 'PyTorch',
          tensorflow: 'TensorFlow',
          'tensorflow-gpu': 'TensorFlow GPU',
          jax: 'JAX',
          'onnxruntime': 'ONNX Runtime',
          'onnxruntime-gpu': 'ONNX Runtime GPU',
          transformers: 'Hugging Face Transformers',
          diffusers: 'Hugging Face Diffusers',
          langchain: 'LangChain',
          'langchain-core': 'LangChain Core',
          llama_cpp_python: 'llama.cpp Python',
          vllm: 'vLLM',
          'text-generation-inference': 'TGI',
          openai: 'OpenAI SDK',
          anthropic: 'Anthropic SDK',
          mlflow: 'MLflow',
          wandb: 'Weights & Biases',
          tensorrt: 'TensorRT',
        };

        for (const pkg of packages) {
          const label = mlPackages[pkg.name.toLowerCase()];
          if (label) {
            runtimes.push({ name: pkg.name, version: pkg.version, type: 'python_ml', label });
            assets.push(this.asset('ai_runtime', `python:${pkg.name}`, { version: pkg.version, label }));
          }
        }
      } catch { /* malformed JSON */ }
    }

    // ── Python version and conda ────────────────────────────────────
    const pythonVersion = this.exec('python3 --version 2>/dev/null') || this.exec('python --version 2>/dev/null');
    if (pythonVersion) {
      runtimes.push({ name: 'python', version: pythonVersion.replace('Python ', ''), type: 'language' });
    }

    const condaVersion = this.exec('conda --version 2>/dev/null');
    if (condaVersion) {
      runtimes.push({ name: 'conda', version: condaVersion.replace('conda ', ''), type: 'env_manager' });
      assets.push(this.asset('ai_runtime', 'conda', { version: condaVersion.replace('conda ', '') }));

      // List conda envs
      const envs = this.exec('conda env list --json 2>/dev/null');
      if (envs) {
        try {
          const parsed = JSON.parse(envs);
          evidence.push(this.evidence('conda_environments', {
            environments: parsed.envs || [],
            count: (parsed.envs || []).length,
          }));
        } catch { /* malformed JSON */ }
      }
    }

    // ── NVIDIA / CUDA ───────────────────────────────────────────────
    const nvidiaSmi = this.exec('nvidia-smi --query-gpu=name,memory.total,driver_version,cuda_version --format=csv,noheader 2>/dev/null');
    if (nvidiaSmi) {
      const gpus = nvidiaSmi.split('\n').filter(Boolean).map((line) => {
        const [name, memory, driver, cuda] = line.split(',').map((s) => s.trim());
        return { name, memory, driver_version: driver, cuda_version: cuda };
      });
      runtimes.push({ name: 'nvidia-cuda', version: gpus[0]?.cuda_version || 'unknown', type: 'gpu' });
      evidence.push(this.evidence('gpu_info', { gpus, count: gpus.length }));
      for (const gpu of gpus) {
        assets.push(this.asset('gpu', gpu.name, { memory: gpu.memory, cuda: gpu.cuda_version }));
      }
    }

    // ── Docker containers running ML workloads ──────────────────────
    if (context.profile === 'deep') {
      const containers = this.exec('docker ps --format "{{.Names}}\t{{.Image}}\t{{.Status}}" 2>/dev/null');
      if (containers) {
        const mlKeywords = ['ollama', 'vllm', 'tgi', 'triton', 'tensorrt', 'torch', 'tensorflow', 'huggingface', 'ml', 'gpu'];
        const mlContainers = containers.split('\n').filter(Boolean).filter((line) =>
          mlKeywords.some((kw) => line.toLowerCase().includes(kw)),
        ).map((line) => {
          const [name, image, status] = line.split('\t');
          return { name, image, status };
        });
        if (mlContainers.length > 0) {
          evidence.push(this.evidence('ml_containers', { containers: mlContainers, count: mlContainers.length }));
        }
      }
    }

    evidence.push(this.evidence('ai_runtimes', { runtimes, count: runtimes.length }));
    return { evidence, assets };
  }
}
