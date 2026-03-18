# ADR-003: Session-Based Authentication

**Status:** Accepted
**Date:** 2026-03-17

## Context

The API needs an authentication mechanism. JWTs are popular but add complexity around revocation and token management. Session-based auth with HttpOnly cookies is simpler and provides immediate revocation.

## Decision

Use session-based authentication with HttpOnly, Secure, SameSite=Strict cookies for the Portal. Session records are stored in the `sessions` table with a hashed token. JWT support is deferred to Beta for third-party API integrations.

## Consequences

- **Positive:** Immediate session revocation by deleting the database row.
- **Positive:** HttpOnly cookies are immune to XSS-based token theft.
- **Negative:** Requires database lookup on every authenticated request (mitigated by Redis caching).
- **Negative:** Third-party integrations must wait for JWT support in Beta (Q4 2026).
