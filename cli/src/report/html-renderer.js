// Local HTML report renderer (§7.5)
// Renders findings, assets, attack paths into a self-contained HTML file
// with inline CSS — no external dependencies.
import { writeFileSync } from 'node:fs';
import logger from '../logger.js';

const SEVERITY_COLORS = {
  critical: '#dc2626',
  high: '#ea580c',
  medium: '#d97706',
  low: '#2563eb',
  info: '#6b7280',
};

const SEVERITY_BG = {
  critical: '#fef2f2',
  high: '#fff7ed',
  medium: '#fffbeb',
  low: '#eff6ff',
  info: '#f9fafb',
};

/**
 * Render the assessment report as a self-contained HTML file.
 *
 * @param {object} reportData — assembled by start.js
 * @param {string} outPath   — file path to write
 */
export async function renderHTML(reportData, outPath) {
  const summary = reportData.summary || {};
  const findings = reportData.findings || [];
  const assets = reportData.assets || [];
  const attackPaths = reportData.attack_paths || [];
  const evidence = reportData.evidence || [];

  const html = `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>BeGuardit Report — ${esc(reportData.session_id)}</title>
<style>
  :root { --bg: #f8fafc; --fg: #0f172a; --border: #e2e8f0; --accent: #2563eb; }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
         background: var(--bg); color: var(--fg); line-height: 1.6; padding: 2rem; max-width: 1100px; margin: 0 auto; }
  h1 { font-size: 1.5rem; margin-bottom: 0.25rem; }
  h2 { font-size: 1.2rem; margin: 2rem 0 1rem; padding-bottom: 0.5rem; border-bottom: 2px solid var(--accent); }
  h3 { font-size: 1rem; margin: 1rem 0 0.5rem; }
  .meta { color: #64748b; font-size: 0.875rem; margin-bottom: 2rem; }
  .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 1rem; margin: 1rem 0; }
  .card { background: #fff; border: 1px solid var(--border); border-radius: 8px; padding: 1rem; text-align: center; }
  .card .num { font-size: 2rem; font-weight: 700; }
  .card .label { font-size: 0.8rem; color: #64748b; text-transform: uppercase; }
  .badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem;
           font-weight: 600; text-transform: uppercase; }
  table { width: 100%; border-collapse: collapse; margin: 1rem 0; font-size: 0.875rem; }
  th, td { padding: 0.5rem 0.75rem; text-align: left; border-bottom: 1px solid var(--border); }
  th { background: #f1f5f9; font-weight: 600; }
  tr:hover { background: #f8fafc; }
  .finding { background: #fff; border: 1px solid var(--border); border-radius: 8px;
             padding: 1rem; margin: 0.75rem 0; border-left: 4px solid; }
  .finding .title { font-weight: 600; margin-bottom: 0.25rem; }
  .finding .desc { font-size: 0.875rem; color: #475569; }
  .finding .remediation { font-size: 0.85rem; color: #059669; margin-top: 0.5rem; }
  .path { background: #fff; border: 1px solid var(--border); border-radius: 8px;
          padding: 1rem; margin: 0.75rem 0; }
  .path-step { display: inline-block; padding: 4px 10px; margin: 2px; border-radius: 4px;
               font-size: 0.8rem; border: 1px solid var(--border); }
  .path-arrow { color: #94a3b8; margin: 0 2px; }
  footer { margin-top: 3rem; padding-top: 1rem; border-top: 1px solid var(--border);
           font-size: 0.8rem; color: #94a3b8; text-align: center; }
</style>
</head>
<body>

<h1>BeGuardit Security Assessment</h1>
<div class="meta">
  Session: <code>${esc(reportData.session_id)}</code><br>
  Host: ${esc(reportData.hostname || 'unknown')} &middot;
  Mode: ${esc(reportData.scan_config?.mode || '?')} &middot;
  Profile: ${esc(reportData.scan_config?.profile || '?')}<br>
  Started: ${esc(reportData.started_at || '')} &middot;
  Completed: ${esc(reportData.completed_at || '')}
</div>

<!-- Summary -->
<h2>Summary</h2>
<div class="grid">
  ${summaryCard(summary.critical || 0, 'Critical', SEVERITY_COLORS.critical)}
  ${summaryCard(summary.high || 0, 'High', SEVERITY_COLORS.high)}
  ${summaryCard(summary.medium || 0, 'Medium', SEVERITY_COLORS.medium)}
  ${summaryCard(summary.low || 0, 'Low', SEVERITY_COLORS.low)}
  ${summaryCard(summary.info || 0, 'Info', SEVERITY_COLORS.info)}
  ${summaryCard(assets.length, 'Assets', '#0ea5e9')}
</div>

<!-- Findings -->
<h2>Findings (${findings.length})</h2>
${findings.length === 0 ? '<p>No findings.</p>' : findings.map((f) => `
<div class="finding" style="border-left-color: ${SEVERITY_COLORS[f.severity] || '#ccc'}">
  <div class="title">
    <span class="badge" style="background: ${SEVERITY_BG[f.severity]}; color: ${SEVERITY_COLORS[f.severity]}">${esc(f.severity)}</span>
    ${esc(f.rule_id)} — ${esc(f.title)}
  </div>
  <div class="desc">${esc(f.description)}</div>
  ${f.remediation ? `<div class="remediation">💡 ${esc(f.remediation)}</div>` : ''}
</div>`).join('')}

<!-- Attack Paths -->
<h2>Attack Paths (${attackPaths.length})</h2>
${attackPaths.length === 0 ? '<p>No attack paths identified.</p>' : attackPaths.map((p) => `
<div class="path">
  <h3>
    <span class="badge" style="background: ${SEVERITY_BG[p.composite_severity]}; color: ${SEVERITY_COLORS[p.composite_severity]}">${esc(p.composite_severity)}</span>
    ${esc(p.id)} (depth ${p.depth})
  </h3>
  <div style="margin-top: 0.5rem">
    ${p.steps.map((s, i) => {
      const color = s.severity ? SEVERITY_COLORS[s.severity] || '#ccc' : '#0ea5e9';
      const bg = s.severity ? SEVERITY_BG[s.severity] || '#f9fafb' : '#f0f9ff';
      return `<span class="path-step" style="background:${bg};border-color:${color}">${esc(s.label)}</span>${i < p.steps.length - 1 ? '<span class="path-arrow">→</span>' : ''}`;
    }).join('')}
  </div>
</div>`).join('')}

<!-- Assets -->
<h2>Assets (${assets.length})</h2>
<table>
  <thead><tr><th>Type</th><th>Name</th></tr></thead>
  <tbody>
    ${assets.slice(0, 100).map((a) => `<tr><td>${esc(a.asset_type)}</td><td>${esc(a.name)}</td></tr>`).join('')}
    ${assets.length > 100 ? `<tr><td colspan="2" style="color:#94a3b8">… and ${assets.length - 100} more</td></tr>` : ''}
  </tbody>
</table>

<!-- Evidence Summary -->
<h2>Evidence (${evidence.length} items)</h2>
<table>
  <thead><tr><th>Collector</th><th>Type</th><th>Collected At</th></tr></thead>
  <tbody>
    ${evidence.slice(0, 50).map((e) => `<tr><td>${esc(e.collector)}</td><td>${esc(e.type)}</td><td>${esc(e.collected_at)}</td></tr>`).join('')}
    ${evidence.length > 50 ? `<tr><td colspan="3" style="color:#94a3b8">… and ${evidence.length - 50} more</td></tr>` : ''}
  </tbody>
</table>

<footer>
  Generated by BeGuardit CLI &middot; ${new Date().toISOString()}
</footer>

</body>
</html>
`;

  writeFileSync(outPath, html, 'utf-8');
  logger.info({ path: outPath }, 'html_report_written');
}

// ── Helpers ──────────────────────────────────────────────────────────

function esc(str) {
  return String(str || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function summaryCard(num, label, color) {
  return `<div class="card"><div class="num" style="color:${color}">${num}</div><div class="label">${label}</div></div>`;
}
