# ADR-009: Ed25519 Release Signing

**Status:** Accepted
**Date:** 2026-03-17

## Context

CLI binaries and release artifacts must be verifiable by end users to ensure integrity and authenticity. We need a signing mechanism that is simple, fast, and uses modern cryptography.

## Decision

Sign all release artifacts with Ed25519 keys via OpenSSL. The public key is embedded in the CLI for self-verification. Signatures are distributed alongside artifacts as `.sig` files. GitHub Actions generates and signs artifacts during the release workflow.

## Consequences

- **Positive:** Ed25519 is fast, produces small signatures, and is widely supported.
- **Positive:** Users can verify artifacts without trusting a third-party CA.
- **Negative:** Key management requires secure storage of the private key (GitHub Actions secrets).
- **Negative:** No certificate chain; trust is based on key distribution rather than a PKI hierarchy.
