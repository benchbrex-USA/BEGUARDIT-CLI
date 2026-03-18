import { describe, it, expect } from 'vitest';
import {
  classifySeverity,
  compareSeverity,
  escalateChain,
  SEVERITY_WEIGHT,
} from '../src/policy/severity.js';

describe('classifySeverity', () => {
  it('returns critical for scores >= 9.0', () => {
    expect(classifySeverity(9.0)).toBe('critical');
    expect(classifySeverity(10.0)).toBe('critical');
    expect(classifySeverity(9.5)).toBe('critical');
  });

  it('returns high for scores 7.0–8.9', () => {
    expect(classifySeverity(7.0)).toBe('high');
    expect(classifySeverity(8.9)).toBe('high');
  });

  it('returns medium for scores 4.0–6.9', () => {
    expect(classifySeverity(4.0)).toBe('medium');
    expect(classifySeverity(6.9)).toBe('medium');
  });

  it('returns low for scores 0.1–3.9', () => {
    expect(classifySeverity(0.1)).toBe('low');
    expect(classifySeverity(3.9)).toBe('low');
  });

  it('returns info for score 0', () => {
    expect(classifySeverity(0)).toBe('info');
  });
});

describe('compareSeverity', () => {
  it('sorts higher severity first', () => {
    expect(compareSeverity('low', 'critical')).toBeGreaterThan(0);
    expect(compareSeverity('critical', 'low')).toBeLessThan(0);
    expect(compareSeverity('high', 'high')).toBe(0);
  });
});

describe('SEVERITY_WEIGHT', () => {
  it('has correct ordering', () => {
    expect(SEVERITY_WEIGHT.critical).toBeGreaterThan(SEVERITY_WEIGHT.high);
    expect(SEVERITY_WEIGHT.high).toBeGreaterThan(SEVERITY_WEIGHT.medium);
    expect(SEVERITY_WEIGHT.medium).toBeGreaterThan(SEVERITY_WEIGHT.low);
    expect(SEVERITY_WEIGHT.low).toBeGreaterThan(SEVERITY_WEIGHT.info);
  });
});

describe('escalateChain', () => {
  it('escalates two high findings to critical', () => {
    expect(escalateChain(['high', 'high'])).toBe('critical');
  });

  it('escalates two medium findings to high', () => {
    expect(escalateChain(['medium', 'medium'])).toBe('high');
  });

  it('escalates three low findings to medium', () => {
    expect(escalateChain(['low', 'low', 'low'])).toBe('medium');
  });

  it('returns single severity unchanged', () => {
    expect(escalateChain(['high'])).toBe('high');
    expect(escalateChain(['low'])).toBe('low');
  });

  it('escalates mixed chain based on max weight', () => {
    expect(escalateChain(['medium', 'high'])).toBe('critical');
  });
});
