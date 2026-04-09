// Report validation — validates canonical report structure before API upload
// Source: ARCH-002-2026-03-17, Section 7.5

const VALID_SEVERITIES = new Set(['critical', 'high', 'medium', 'low', 'info']);

/**
 * Validate a canonical report object before uploading to the API.
 * @param {object} data - The report data object
 * @returns {{ valid: boolean, errors: string[] }}
 */
export function validateReport(data) {
  const errors = [];

  if (!data || typeof data !== 'object') {
    return { valid: false, errors: ['Report data must be a non-null object'] };
  }

  // session_id
  if (!data.session_id || typeof data.session_id !== 'string') {
    errors.push('session_id is required and must be a non-empty string');
  }

  // hostname
  if (!data.hostname || typeof data.hostname !== 'string') {
    errors.push('hostname is required and must be a non-empty string');
  }

  // assets
  if (!Array.isArray(data.assets)) {
    errors.push('assets must be an array');
  } else {
    for (let i = 0; i < data.assets.length; i++) {
      const a = data.assets[i];
      if (!a.asset_type || typeof a.asset_type !== 'string') {
        errors.push(`assets[${i}].asset_type is required and must be a string`);
      }
      if (!a.name || typeof a.name !== 'string') {
        errors.push(`assets[${i}].name is required and must be a string`);
      }
    }
  }

  // findings
  if (!Array.isArray(data.findings)) {
    errors.push('findings must be an array');
  } else {
    for (let i = 0; i < data.findings.length; i++) {
      const f = data.findings[i];
      if (!f.rule_id || typeof f.rule_id !== 'string') {
        errors.push(`findings[${i}].rule_id is required and must be a string`);
      }
      if (!f.title || typeof f.title !== 'string') {
        errors.push(`findings[${i}].title is required and must be a string`);
      }
      if (!f.severity || !VALID_SEVERITIES.has(f.severity)) {
        errors.push(`findings[${i}].severity must be one of: critical, high, medium, low, info`);
      }
    }
  }

  // evidence
  if (!Array.isArray(data.evidence)) {
    errors.push('evidence must be an array');
  } else {
    for (let i = 0; i < data.evidence.length; i++) {
      const e = data.evidence[i];
      if (!e.collector || typeof e.collector !== 'string') {
        errors.push(`evidence[${i}].collector is required and must be a string`);
      }
      if (!e.type || typeof e.type !== 'string') {
        errors.push(`evidence[${i}].type is required and must be a string`);
      }
    }
  }

  return { valid: errors.length === 0, errors };
}
