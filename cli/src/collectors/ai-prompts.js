// AI collector: ai-prompts (§7.2)
// Discovers: prompt template files, LangChain prompt stores, .prompt directories
// Profiles: standard, deep
import { existsSync, readdirSync, readFileSync, statSync } from 'node:fs';
import { homedir } from 'node:os';
import { join } from 'node:path';
import BaseCollector from './base.js';

export default class AiPromptsCollector extends BaseCollector {
  constructor() {
    super();
    this.name = 'ai-prompts';
    this.category = 'ai';
    this.platforms = ['linux', 'darwin', 'win32'];
    this.profiles = ['standard', 'deep'];
  }

  async collect(context) {
    const evidence = [];
    const assets = [];

    const searchRoots = [
      process.cwd(),
      join(homedir(), 'projects'),
      join(homedir(), 'code'),
      join(homedir(), 'src'),
    ];

    // ── Prompt template files ───────────────────────────────────────
    const promptExtensions = ['prompt', 'prompts', 'jinja', 'jinja2', 'mustache', 'hbs'];
    const extArgs = promptExtensions.map((e) => `-name "*.${e}"`).join(' -o ');

    const promptFiles = [];
    for (const root of searchRoots) {
      if (!existsSync(root)) continue;
      const found = this.exec(
        `find "${root}" -maxdepth 4 \\( ${extArgs} \\) -type f 2>/dev/null | head -50`,
      );
      if (found) {
        for (const filePath of found.split('\n').filter(Boolean)) {
          try {
            const stat = statSync(filePath);
            promptFiles.push({
              path: filePath,
              size_bytes: stat.size,
              extension: filePath.split('.').pop(),
            });
          } catch { /* stat failed */ }
        }
      }
    }
    evidence.push(this.evidence('prompt_template_files', {
      files: promptFiles,
      count: promptFiles.length,
    }));

    // ── .prompts / prompts / prompt directories ─────────────────────
    const promptDirNames = ['prompts', '.prompts', 'prompt_templates', 'prompt-templates', 'system_prompts'];
    const promptDirs = [];

    for (const root of searchRoots) {
      if (!existsSync(root)) continue;
      for (const dirName of promptDirNames) {
        const found = this.exec(
          `find "${root}" -maxdepth 3 -type d -name "${dirName}" 2>/dev/null | head -20`,
        );
        if (found) {
          for (const dir of found.split('\n').filter(Boolean)) {
            try {
              const files = readdirSync(dir).filter((f) => !f.startsWith('.'));
              promptDirs.push({ path: dir, file_count: files.length });
              assets.push(this.asset('prompt_store', dir, { file_count: files.length }));
            } catch { /* readdir failed */ }
          }
        }
      }
    }
    evidence.push(this.evidence('prompt_directories', {
      directories: promptDirs,
      count: promptDirs.length,
    }));

    // ── LangChain / LlamaIndex prompt patterns ──────────────────────
    const lcPatterns = [
      'ChatPromptTemplate',
      'PromptTemplate',
      'SystemMessagePromptTemplate',
      'HumanMessagePromptTemplate',
      'FewShotPromptTemplate',
    ];
    const patternGlob = lcPatterns.map((p) => `-e "${p}"`).join(' ');
    const lcFiles = [];

    for (const root of searchRoots) {
      if (!existsSync(root)) continue;
      const found = this.exec(
        `grep -rl ${patternGlob} "${root}" --include="*.py" 2>/dev/null | head -30`,
      );
      if (found) {
        for (const filePath of found.split('\n').filter(Boolean)) {
          lcFiles.push({ path: filePath });
        }
      }
    }
    evidence.push(this.evidence('langchain_prompt_usage', {
      files: lcFiles,
      count: lcFiles.length,
    }));

    // ── System prompt strings in code (deep) ────────────────────────
    if (context.profile === 'deep') {
      const systemPromptPatterns = ['system_prompt', 'system_message', 'SYSTEM_PROMPT', 'systemPrompt'];
      const spGlob = systemPromptPatterns.map((p) => `-e "${p}"`).join(' ');
      const spFiles = [];

      for (const root of searchRoots) {
        if (!existsSync(root)) continue;
        const found = this.exec(
          `grep -rl ${spGlob} "${root}" --include="*.py" --include="*.js" --include="*.ts" 2>/dev/null | head -30`,
        );
        if (found) {
          for (const filePath of found.split('\n').filter(Boolean)) {
            spFiles.push({ path: filePath });
          }
        }
      }
      evidence.push(this.evidence('system_prompt_references', {
        files: spFiles,
        count: spFiles.length,
      }));
    }

    for (const pf of promptFiles) {
      assets.push(this.asset('prompt_template', pf.path, { extension: pf.extension }));
    }

    return { evidence, assets };
  }
}
