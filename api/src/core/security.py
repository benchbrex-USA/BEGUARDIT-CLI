# Core — password hashing (argon2id), session token helpers
# Source: ARCH-002-2026-03-17, ADR-003 / ADR-010
# argon2id params: memory=64 MiB, iterations=3, parallelism=4
from __future__ import annotations

import hashlib
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

# ---------------------------------------------------------------------------
# Password hashing — argon2id (§ADR-010)
# ---------------------------------------------------------------------------

_ph = PasswordHasher(
    time_cost=3,          # iterations
    memory_cost=65536,    # 64 MiB
    parallelism=4,
    hash_len=32,
    salt_len=16,
    type=__import__("argon2").Type.ID,  # argon2id
)


def hash_password(password: str) -> str:
    """Hash a plaintext password with argon2id."""
    return _ph.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a plaintext password against an argon2id hash.

    Returns True if valid, False if mismatch.
    """
    try:
        return _ph.verify(password_hash, password)
    except VerifyMismatchError:
        return False


def needs_rehash(password_hash: str) -> bool:
    """Check if the hash parameters are outdated and need rehashing."""
    return _ph.check_needs_rehash(password_hash)


# ---------------------------------------------------------------------------
# Session tokens (§ADR-003)
# ---------------------------------------------------------------------------

def generate_session_token() -> str:
    """Generate a cryptographically random session token (URL-safe, 32 bytes)."""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """SHA-256 hash of a session token for DB storage."""
    return hashlib.sha256(token.encode()).hexdigest()
