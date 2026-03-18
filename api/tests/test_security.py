# Tests for src.core.security — password hashing and session tokens
import pytest
from src.core.security import (
    generate_session_token,
    hash_password,
    hash_token,
    needs_rehash,
    verify_password,
)


class TestPasswordHashing:
    def test_hash_returns_argon2id_string(self):
        h = hash_password("testpass123")
        assert h.startswith("$argon2id$")

    def test_verify_correct_password(self):
        h = hash_password("correct-horse-battery-staple")
        assert verify_password("correct-horse-battery-staple", h) is True

    def test_verify_wrong_password(self):
        h = hash_password("correct-horse-battery-staple")
        assert verify_password("wrong-password", h) is False

    def test_different_passwords_produce_different_hashes(self):
        h1 = hash_password("password1")
        h2 = hash_password("password2")
        assert h1 != h2

    def test_same_password_produces_different_hashes_salt(self):
        h1 = hash_password("same-password")
        h2 = hash_password("same-password")
        assert h1 != h2  # different salt each time

    def test_needs_rehash_current_params(self):
        h = hash_password("test")
        assert needs_rehash(h) is False


class TestSessionTokens:
    def test_generate_token_is_string(self):
        token = generate_session_token()
        assert isinstance(token, str)
        assert len(token) > 20

    def test_generate_tokens_are_unique(self):
        tokens = {generate_session_token() for _ in range(100)}
        assert len(tokens) == 100

    def test_hash_token_is_hex(self):
        token = generate_session_token()
        h = hash_token(token)
        assert len(h) == 64  # SHA-256 hex
        int(h, 16)  # must be valid hex

    def test_hash_token_deterministic(self):
        token = generate_session_token()
        assert hash_token(token) == hash_token(token)

    def test_different_tokens_different_hashes(self):
        t1 = generate_session_token()
        t2 = generate_session_token()
        assert hash_token(t1) != hash_token(t2)
