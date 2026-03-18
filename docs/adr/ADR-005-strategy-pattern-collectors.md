# ADR-005: Strategy Pattern for CLI Collectors

**Status:** Accepted
**Date:** 2026-03-17

## Context

The CLI must collect diverse types of host evidence (OS info, network config, packages, AI runtimes, etc.). Each collector has different logic, dependencies, and platform requirements. We need an extensible way to add new collectors without modifying core scan logic.

## Decision

Implement collectors using the Strategy pattern. Each collector is an independent module that implements a common interface (`collect() -> CollectorResult`). Collectors are registered in a manifest and can be enabled or disabled per scan configuration.

## Consequences

- **Positive:** New collectors can be added without touching existing code.
- **Positive:** Collectors can be tested in isolation.
- **Positive:** Scan configurations can selectively enable collectors per use case.
- **Negative:** Slight indirection overhead; developers must follow the collector interface contract.
