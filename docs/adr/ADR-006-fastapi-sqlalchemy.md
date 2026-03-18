# ADR-006: FastAPI + SQLAlchemy 2.0 for API Backend

**Status:** Accepted
**Date:** 2026-03-17

## Context

The API backend needs a Python web framework and ORM. Key requirements: async support, OpenAPI generation, type safety, and mature PostgreSQL support.

## Decision

Use FastAPI 0.115+ for the web framework and SQLAlchemy 2.0+ with asyncpg for the ORM/database layer. Alembic handles schema migrations. Pydantic v2 provides request/response validation.

## Consequences

- **Positive:** Automatic OpenAPI docs, native async, excellent type checking with Pydantic v2.
- **Positive:** SQLAlchemy 2.0 mapped_column style provides clear, type-annotated models.
- **Positive:** Large ecosystem and community support for both FastAPI and SQLAlchemy.
- **Negative:** SQLAlchemy async has some quirks around lazy loading (mitigated by using `selectin`/`joined` strategies).
