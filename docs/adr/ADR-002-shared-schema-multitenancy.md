# ADR-002: Shared-Schema Multi-Tenancy

**Status:** Accepted
**Date:** 2026-03-17

## Context

BeGuardit must support multiple tenants (organizations). The options are: database-per-tenant, schema-per-tenant, or shared-schema with a discriminator column.

## Decision

Use shared-schema multi-tenancy with a `tenant_id` column on every business table. Row-Level Security (RLS) policies in PostgreSQL provide defence-in-depth enforcement at the database layer.

## Consequences

- **Positive:** Single database to manage, simpler migrations, lower operational cost.
- **Positive:** RLS prevents accidental cross-tenant data leaks even if application code has a bug.
- **Negative:** All queries must include `tenant_id` filtering; missing filters could expose data (mitigated by RLS).
- **Negative:** Very large tenants may cause hot-spot contention; acceptable at current scale.
