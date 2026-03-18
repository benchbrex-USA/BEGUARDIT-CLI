# ADR-010: Argon2id for Password Hashing

**Status:** Accepted
**Date:** 2026-03-17

## Context

User passwords must be hashed before storage. The industry has moved beyond SHA-256 and bcrypt toward memory-hard algorithms that resist GPU and ASIC attacks. Argon2id (winner of the Password Hashing Competition) is the current recommendation from OWASP.

## Decision

Use Argon2id as the primary password hashing algorithm. Bcrypt (12 rounds) is retained as a fallback for environments where the argon2 C library is unavailable. Hashes are stored in PHC string format in the `users.password_hash` column.

## Consequences

- **Positive:** Argon2id provides strong resistance against brute-force, GPU, and side-channel attacks.
- **Positive:** PHC format is self-describing; algorithm upgrades can be applied transparently on next login (rehash-on-verify pattern).
- **Negative:** Argon2id requires a native C extension (`argon2-cffi`); adds a build dependency.
- **Negative:** Higher memory usage per hash operation compared to bcrypt; acceptable for auth endpoints with rate limiting.
