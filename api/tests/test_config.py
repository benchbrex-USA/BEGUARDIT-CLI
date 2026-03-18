# Tests for src.core.config — Settings
import pytest
from src.core.config import Settings


class TestSettings:
    def test_defaults(self):
        s = Settings(DATABASE_URL="postgresql+asyncpg://x:y@localhost/db")
        assert s.SESSION_TTL_SECONDS == 86400
        assert s.RATE_LIMIT_DEFAULT == 100
        assert s.RATE_LIMIT_LOGIN == 10
        assert s.LOG_LEVEL == "INFO"
        assert s.BCRYPT_ROUNDS == 12

    def test_cors_origins_list_single(self):
        s = Settings(
            DATABASE_URL="postgresql+asyncpg://x:y@localhost/db",
            CORS_ORIGINS="http://localhost:5173",
        )
        assert s.cors_origins_list == ["http://localhost:5173"]

    def test_cors_origins_list_multiple(self):
        s = Settings(
            DATABASE_URL="postgresql+asyncpg://x:y@localhost/db",
            CORS_ORIGINS="http://localhost:5173,https://app.beguardit.com",
        )
        assert s.cors_origins_list == ["http://localhost:5173", "https://app.beguardit.com"]

    def test_cors_origins_list_strips_whitespace(self):
        s = Settings(
            DATABASE_URL="postgresql+asyncpg://x:y@localhost/db",
            CORS_ORIGINS="  http://a.com , http://b.com  ",
        )
        assert s.cors_origins_list == ["http://a.com", "http://b.com"]
