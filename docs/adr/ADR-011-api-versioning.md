# ADR-011: API Versioning Strategy

**Status:** Accepted
**Date:** 2026-03-18

## Context

All BeGuardit API endpoints are currently served under the `/api/v1/` prefix. As the product transitions from Beta to General Availability (GA), we need a clear versioning strategy that:

- Allows breaking changes to be introduced without disrupting existing integrations (CLI agents, portal, third-party consumers).
- Gives consumers sufficient notice and migration time before old versions are removed.
- Keeps the implementation simple and predictable for a small team.

The CLI (`beguardit start --mode online`) and the React portal are the primary API consumers today, but the public API surface will grow as enterprise customers integrate with CI/CD pipelines and SIEMs.

## Decision

Adopt **URL-based versioning** with a **6-month deprecation window** and standard HTTP deprecation headers.

### Versioning scheme

- Major versions are embedded in the URL path: `/api/v1/`, `/api/v2/`, etc.
- A new major version is introduced only when a breaking change is required (removed fields, changed semantics, restructured resources).
- Non-breaking additions (new optional fields, new endpoints) are added to the current version without a version bump.

### Deprecation policy

1. When a new version `vN+1` is released, the previous version `vN` enters a **6-month deprecation period**.
2. During deprecation, responses from `vN` include two headers:
   - `Deprecation: true` (RFC 8594)
   - `Sunset: <date>` — the ISO-8601 date after which `vN` will be removed.
3. Documentation and changelog entries announce the deprecation, with a migration guide.
4. After the sunset date, requests to the deprecated version return `410 Gone` with a JSON body pointing to the successor version.

### Implementation details

- FastAPI sub-applications or routers are used per version: `app.include_router(v1_router, prefix="/api/v1")`.
- A middleware layer injects `Deprecation` and `Sunset` headers for deprecated versions based on a configuration map.
- Health-check and non-versioned routes (`/healthz`, `/readyz`) remain outside the versioned prefix.
- OpenAPI specs are generated per version (`/api/v1/openapi.json`, `/api/v2/openapi.json`).

## Rejected Alternatives

### Header-based versioning (`Accept: application/vnd.beguardit.v2+json`)

- **Pros:** Cleaner URLs; follows REST purist principles.
- **Cons:** Harder to test (requires custom headers in browsers and curl); not cache-friendly without `Vary` header management; harder for operators to understand at a glance which version they are calling; limited tooling support in API gateways.

### Query parameter versioning (`?version=2`)

- **Pros:** Easy to add ad hoc.
- **Cons:** Mixes versioning with query semantics; breaks caching; easy to forget; not a widely adopted convention for production APIs; makes OpenAPI spec generation ambiguous.

## Consequences

- **Positive:** URL-based versioning is the most widely understood pattern. Consumers can see the version in every request/response log, making debugging straightforward.
- **Positive:** The 6-month deprecation window with HTTP headers gives automated systems (and humans) machine-readable signals to plan migrations.
- **Positive:** OpenAPI specs per version enable accurate SDK generation for each version independently.
- **Negative:** Multiple versioned routers must be maintained in parallel during the deprecation window, increasing code surface temporarily.
- **Negative:** URL-based versioning can lead to full router duplication if not managed carefully; shared service layers and schemas should be used to minimize drift.
