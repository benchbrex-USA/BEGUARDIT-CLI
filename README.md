<p align="center">
  <img src="https://img.shields.io/badge/BeGuardit-CLI-0ea5e9?style=for-the-badge&logo=shield&logoColor=white" alt="BeGuardit CLI" />
  <img src="https://img.shields.io/badge/License-Proprietary-333?style=for-the-badge" alt="License" />
  <img src="https://img.shields.io/badge/Status-Alpha-orange?style=for-the-badge" alt="Status" />
</p>

<h1 align="center">BeGuardit CLI</h1>

<p align="center">
  <strong>Terminal-first cybersecurity & AI security assessment platform</strong><br/>
  <em>Collect. Analyze. Remediate. — All from your terminal.</em>
</p>

<p align="center">
  <a href="#quick-start">Quick Start</a> &bull;
  <a href="#architecture">Architecture</a> &bull;
  <a href="#features">Features</a> &bull;
  <a href="#multi-agent-pipeline">Multi-Agent Pipeline</a> &bull;
  <a href="#documentation">Docs</a>
</p>

---

## What is BeGuardit?

BeGuardit is a **zero-footprint security assessment tool** that runs entirely from the command line. It collects host-level evidence, evaluates it against security policies, identifies attack paths through correlation analysis, and generates actionable reports — all without installing persistent agents on your infrastructure.

```
$ beguardit start --profile deep --mode online

┌─────────────────────────────────────────┐
│        BeGuardit Assessment Start        │
├─────────────────────────────────────────┤
│  Session:    a3f8c1d2-...               │
│  Mode:       online                     │
│  Profile:    deep                       │
│  Categories: cyber, ai                  │
└─────────────────────────────────────────┘

▸ Collecting evidence...
  ✓ 247 evidence items from 18 assets

▸ Evaluating policies...
  ✓ 34 findings (2 critical, 5 high, 12 medium)

▸ Building correlation graph...
  ✓ 3 attack paths identified

▸ Generating reports...
  ✓ JSON report: ./output/a3f8c1d2.json
  ✓ HTML report: ./output/a3f8c1d2.html

▸ Uploading to API...
  ✓ Uploaded successfully

Assessment complete.
```

---

## Features

### Security Assessment Engine
- **10+ built-in collectors** — OS info, network, services, packages, users/auth, filesystem, AI runtimes, AI models, prompt injection vectors, RAG pipelines
- **Policy evaluation engine** — rule-based analysis with severity scoring (critical / high / medium / low / info)
- **Attack path correlation** — graph-based analysis to identify multi-step attack chains
- **Three scan profiles** — Quick (critical checks), Standard (balanced), Deep (full coverage)

### Multi-Format Reporting
- **Canonical JSON** — SHA-256 integrity hash, machine-readable
- **HTML** — Styled inline reports with severity breakdown, finding details, and asset inventory
- **PDF** — Production-ready reports via WeasyPrint rendering
- **SARIF v2.1.0** — GitHub Code Scanning & Azure DevOps integration

### AI / ML Security Posture
- **AI runtime detection** — Identify running inference servers, model registries, GPU allocations
- **Model inventory** — Catalog deployed models with versioning and access controls
- **Prompt injection analysis** — Detect exposed prompt endpoints and injection vectors
- **RAG pipeline audit** — Evaluate retrieval-augmented generation security boundaries

### Enterprise-Grade Platform
- **Multi-tenant architecture** — Shared-schema PostgreSQL with row-level security
- **RBAC** — Admin, Operator, Viewer roles per tenant
- **Session-based auth** — Argon2id hashing, CSRF protection, HttpOnly cookies
- **Async report generation** — ARQ worker queue with Redis, idempotent job execution
- **S3-compatible storage** — Local, AWS S3, Cloudflare R2, MinIO

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        BeGuardit Platform                        │
├──────────┬──────────┬──────────┬──────────┬──────────┬──────────┤
│   CLI    │   API    │  Worker  │  Portal  │  Site    │  Infra   │
│ Node.js  │ FastAPI  │ ARQ+Redis│ React 18 │ Astro 4  │ K8s      │
│ 20 LTS   │ Py 3.12+ │ Py 3.12+│ Vite+TS  │ Static   │ Docker   │
└──────────┴──────────┴──────────┴──────────┴──────────┴──────────┘
     │           │           │           │
     │     ┌─────┴─────┐     │           │
     └────►│PostgreSQL │◄────┘           │
           │   16      │                 │
           └─────┬─────┘                 │
                 │                       │
           ┌─────┴─────┐                │
           │  Redis 7  │◄───────────────┘
           └───────────┘
```

| Component | Stack | Purpose |
|-----------|-------|---------|
| **CLI** | Node.js 20, Commander.js, Inquirer.js | Evidence collection, policy evaluation, local reporting |
| **API** | FastAPI, SQLAlchemy 2.0 async, Pydantic v2 | REST API, auth, tenant management, assessment storage |
| **Worker** | ARQ, Redis 7 | Async report generation (HTML, PDF, SARIF), scheduled maintenance |
| **Portal** | React 18, TypeScript strict, Tailwind CSS 3 | Web dashboard, assessment viewer, report management |
| **Site** | Astro 4 | Public documentation and marketing |
| **Infra** | Docker Compose, Kubernetes, Nginx, GitHub Actions | Deployment, CI/CD, TLS termination |

---

## Multi-Agent Pipeline

BeGuardit's assessment engine uses a **multi-agent architecture** where independent collector agents run in parallel, each specialized for a specific evidence domain:

```
                    ┌─── Cyber Agents ───┐
                    │                    │
Session ──► Runner ─┤  os-info           │
                    │  network           │──► Policy Engine ──► Correlator ──► Reports
                    │  services          │
                    │  packages          │
                    │  users-auth        │
                    │  filesystem        │
                    │                    │
                    ├─── AI Agents ──────┤
                    │                    │
                    │  ai-runtimes       │
                    │  ai-models         │
                    │  ai-prompts        │
                    │  ai-rag            │
                    └────────────────────┘
```

Each agent:
- Executes independently with its own error boundary
- Reports partial results even if other agents fail
- Is profile-aware (quick/standard/deep) to control scan depth
- Threads session context for evidence correlation

The **correlation engine** builds a directed graph across all agent outputs, identifying multi-step attack paths that no single agent could detect alone.

---

## Quick Start

### Install CLI

```bash
npm install -g @beguardit/cli
```

### Run Your First Assessment

```bash
# Interactive guided mode
beguardit start

# Or with flags
beguardit start --mode offline --profile standard --categories cyber,ai
```

### Check System Prerequisites

```bash
beguardit doctor
```

### Full Platform (Docker)

```bash
git clone https://github.com/benchbrex-USA/BEGUARDIT-CLI.git
cd BEGUARDIT-CLI
cp .env.example .env
docker compose -f infra/docker-compose.yml up
```

Portal: `http://localhost:5173` | API: `http://localhost:8000/api/v1/docs`

---

## CLI Commands

| Command | Description |
|---------|-------------|
| `beguardit start` | Run a security assessment (interactive or flags) |
| `beguardit doctor` | Verify system prerequisites and dependencies |
| `beguardit report` | Generate reports from existing assessment data |
| `beguardit upload <file>` | Upload a local assessment to the API |
| `beguardit config` | View or update CLI configuration |
| `beguardit version` | Print CLI and platform version info |
| `beguardit uninstall` | Clean up CLI data and configuration |

---

## API Endpoints

| Group | Endpoints | Auth |
|-------|-----------|------|
| **Auth** | `POST /login` `POST /register` `POST /logout` `POST /me` `POST /switch-tenant` `POST /reset` | Public / Session |
| **Assessments** | `GET /` `GET /:id` `GET /:id/findings` `GET /:id/assets` `GET /:id/evidence` `DELETE /:id` | Session + RBAC |
| **Reports** | `POST /` `GET /` `GET /:id` `GET /:id/download` | Session + RBAC |
| **Upload** | `POST /assessment` | Session |
| **Tenants** | `GET /` `PATCH /` `GET /members` `POST /members` | Session + Admin |
| **Admin** | `GET /users` `PATCH /users/:id` `GET /audit-log` | Session + Admin |
| **Health** | `GET /health` `GET /ready` | Public |

Full OpenAPI docs available at `/api/v1/docs` when running.

---

## Documentation

- **[Architecture Spec](docs/architecture.md)** — Full system design, data flow, and evolution roadmap
- **[ADR-001: Modular Layered Architecture](docs/adr/ADR-001-modular-layered.md)** — Why monorepo over microservices
- **[Runbooks](docs/runbooks/)** — Operational procedures and incident response

---

## Roadmap

| Phase | Timeline | Focus |
|-------|----------|-------|
| **Alpha** | Q1-Q2 2026 | Core CLI + API + Portal, HTML reports |
| **Stronger Alpha** | Q3 2026 | Expanded collectors, improved UX |
| **Beta** | Q4 2026 | PDF/SARIF reports, MFA, API keys |
| **GA** | H1 2027 | Commercial licensing, SLA |
| **Growth** | H2 2027+ | On-prem, microservices evaluation |

---

## Development

```bash
# API
cd api && pip install -e ".[dev]" && pytest

# CLI
cd cli && npm install && npm test

# Portal
cd portal && npm install && npm run dev

# Worker
cd worker && pip install -e ".[dev]" && arq src.main.WorkerSettings
```

---

## Security

BeGuardit takes security seriously. If you discover a vulnerability, please report it responsibly via [security@beguardit.com](mailto:security@beguardit.com).

---

<p align="center">
  <strong>Built by <a href="https://github.com/benchbrex-USA">Benchbrex</a></strong><br/>
  <sub>Securing infrastructure, one assessment at a time.</sub>
</p>
