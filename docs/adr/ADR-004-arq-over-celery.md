# ADR-004: ARQ Over Celery for Async Jobs

**Status:** Accepted
**Date:** 2026-03-17

## Context

The worker component processes async jobs (report generation). Celery is the most common Python task queue but requires a message broker (RabbitMQ or Redis) and has significant configuration surface. ARQ is a lightweight alternative built on Redis and asyncio.

## Decision

Use ARQ 0.26+ as the task queue. It uses Redis (which we already need for caching) and is natively async, matching our asyncpg/SQLAlchemy async stack.

## Consequences

- **Positive:** Fewer dependencies; no RabbitMQ required.
- **Positive:** Native async/await; consistent with the rest of the Python codebase.
- **Positive:** Simpler configuration and smaller codebase.
- **Negative:** Smaller community and ecosystem compared to Celery.
- **Negative:** Limited built-in features (no canvas/chord patterns); acceptable for our use case.
