# BeGuardit CLI — Architecture Overview

Reference: ARCH-002-2026-03-17 (Full-Stack Architecture Specification v1)

## System Purpose

BeGuardit is a terminal-first cybersecurity and AI security assessment platform.
It collects host-level evidence via a CLI tool, analyses findings server-side,
and presents results through a web portal with exportable reports.

## Components

The system follows a **modular layered** architecture (not microservices).
All components live in a single monorepo.

| Component | Tech Stack | Role |
|-----------|-----------|------|
| **CLI** | Node.js 20 LTS, Commander.js, Inquirer.js | Runs on target host; collects evidence via strategy-pattern collectors |
| **API** | Python 3.12+, FastAPI 0.115+, SQLAlchemy 2.0, Alembic | REST backend; auth, RBAC, assessments, upload, reports |
| **Worker** | Python 3.12+, ARQ 0.26+ (Redis) | Async job processing; HTML/PDF/SARIF report generation |
| **Portal** | React 18, TypeScript, Vite 5, Tailwind CSS 3 | Web dashboard for viewing assessments, findings, and reports |
| **Public Site** | Astro 4 (static) | Marketing, docs, install instructions |
| **Release Pipeline** | GitHub Actions, OpenSSL Ed25519 | CI/CD, artifact signing, container builds |

## Infrastructure

- **Database:** PostgreSQL 16 with shared-schema multi-tenancy (`tenant_id` on every table, RLS as defence-in-depth).
- **Queue:** Redis 7 (ARQ job queue for worker).
- **Reverse Proxy:** Nginx (TLS termination, static file serving).
- **Dev:** Docker Compose (postgres, redis, api, worker, portal).
- **Prod:** Kubernetes (namespace per environment, Deployments + Services).

## Data Flow

```
CLI (target host)
  |  HTTPS POST /api/v1/assessments/{id}/upload
  v
API (FastAPI)
  |  Validates, stores in PostgreSQL, enqueues report jobs
  v
Redis (ARQ queue)
  |
  v
Worker (ARQ)
  |  Generates HTML/PDF/SARIF, writes to storage, updates DB
  v
Portal (React SPA)
  |  Reads assessments, findings, reports via API
  v
User (browser)
```

## Database Schema

Core tables: `tenants`, `users`, `memberships`, `sessions`, `assessment_sessions`,
`assets`, `evidence`, `findings`, `report_jobs`, `audit_log`.

Every table includes `tenant_id` for multi-tenant isolation. Row-level security
policies enforce tenant boundaries at the database layer.

## Authentication and Authorization

- **Auth method:** Session-based (HttpOnly cookies). JWT planned for Beta (3rd-party integrations).
- **Password hashing:** Argon2id (primary), bcrypt (fallback).
- **RBAC roles:** `admin`, `operator`, `viewer` — enforced per tenant via the `memberships` table.
- **Rate limiting:** Per-IP and per-email limits on auth endpoints.

## CLI Collectors

Collectors follow the Strategy pattern. Each collector is an independent module
that can be enabled or disabled per scan configuration.

**Cyber collectors:** os-info, network, services, packages, users-auth, filesystem.
**AI collectors:** ai-runtimes, ai-models, ai-prompts, ai-rag.

## API Surface

Base URL: `/api/v1`

Key endpoint groups: auth, tenants, assessments, upload, reports, admin, health.
All mutations are logged to the `audit_log` table.

## Deployment

- **Local dev:** `docker compose up` from `infra/`.
- **Production:** Kubernetes manifests in `infra/k8s/`. Deploy script at `infra/scripts/deploy.sh`.
- **CI/CD:** GitHub Actions workflows in `.github/workflows/`.

## Evolution Roadmap

| Phase | Timeline | Highlights |
|-------|----------|-----------|
| Alpha | Q1-Q2 2026 | Core CLI + API + Portal, HTML reports |
| Stronger Alpha | Q3 2026 | Expanded collectors, improved UX |
| Beta | Q4 2026 | PDF/SARIF reports, MFA, API keys, JWT |
| GA | H1 2027 | Commercial licensing, SLA |
| Growth | H2 2027+ | On-prem option, microservices evaluation |

## Architecture Decision Records

See `docs/adr/` for the full set of ADRs (ADR-001 through ADR-010).
