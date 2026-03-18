# ADR-001: Modular Layered Architecture

**Status:** Accepted
**Date:** 2026-03-17

## Context

We need to choose between a microservices architecture and a modular monolith for the initial product. The team is small (single developer), and the system has six logical components that share a database and deployment lifecycle.

## Decision

Adopt a modular layered architecture. Each component (CLI, API, Worker, Portal, Site, Pipeline) is a separate directory in a monorepo with clear boundaries, but they are not independently deployed microservices. The API and Worker share the same database schema and ORM models.

## Consequences

- **Positive:** Simpler deployment, no inter-service networking overhead, easier debugging, single DB schema to manage.
- **Positive:** Components can be extracted into microservices later if scaling demands it (Growth phase, H2 2027+).
- **Negative:** Tight coupling risk if module boundaries are not enforced through code review discipline.
- **Negative:** Horizontal scaling is coarser-grained (scale entire API, not individual endpoints).
