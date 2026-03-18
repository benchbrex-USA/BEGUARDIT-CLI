# ADR-007: React + Tailwind CSS for Portal

**Status:** Accepted
**Date:** 2026-03-17

## Context

The portal needs a modern SPA framework. Requirements: TypeScript support, fast development cycle, component-based architecture, and no heavy UI library dependency.

## Decision

Use React 18 with TypeScript, Vite 5 as the build tool, and Tailwind CSS 3 for styling. TanStack Query handles server-state management. No Redux or external component library (e.g., Material UI) -- all components are custom Tailwind-based.

## Consequences

- **Positive:** Full control over design; no dependency on third-party component library release cycles.
- **Positive:** Vite provides fast HMR and build times; TanStack Query simplifies data fetching and caching.
- **Positive:** Tailwind utility classes keep CSS co-located and reduce stylesheet bloat.
- **Negative:** Custom components require more upfront development time than using a component library.
- **Negative:** No built-in accessibility primitives; must be implemented manually.
