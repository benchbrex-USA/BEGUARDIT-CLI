# ADR-008: Node.js for CLI (Go Post-Beta)

**Status:** Accepted
**Date:** 2026-03-17

## Context

The CLI runs on customer machines to collect evidence. It needs to be cross-platform (macOS, Linux, Windows), easy to install, and fast to develop. Long-term, a compiled single-binary distribution (Go) is preferred for deployment simplicity.

## Decision

Build the initial CLI in Node.js 20 LTS using Commander.js (command parsing) and Inquirer.js (interactive prompts). Plan migration to Go after Beta when the collector interface is stable and performance/distribution requirements increase.

## Consequences

- **Positive:** Rapid prototyping; rich npm ecosystem for system interaction.
- **Positive:** JavaScript/TypeScript skills transfer from Portal development.
- **Negative:** Requires Node.js runtime on target machines (mitigated by bundling with pkg/nexe if needed).
- **Negative:** Future Go rewrite is a planned cost; accepted as a deliberate phased strategy.
