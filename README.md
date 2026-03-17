# BeGuardit CLI

Terminal-first cybersecurity and AI security assessment platform.

## Monorepo structure

| Directory | Component | Tech |
|---|---|---|
| `cli/` | CLI collector | Node.js 20 |
| `api/` | API backend | FastAPI + PostgreSQL |
| `worker/` | Async report worker | ARQ + Redis |
| `portal/` | Web portal | React 18 + Vite |
| `site/` | Public docs site | Astro 4 |
| `infra/` | Docker / K8s / Nginx | — |
| `docs/` | Architecture, ADRs, specs | — |

## Quick start

```bash
cp .env.example .env
docker compose -f infra/docker-compose.yml up
```

See `docs/architecture.md` and the full architecture spec (ARCH-002-2026-03-17) for implementation details.
