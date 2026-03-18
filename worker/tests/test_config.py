# Tests for WorkerConfig — validates defaults and env-var overrides
from __future__ import annotations

import os
from unittest import mock

import pytest

from src.config import WorkerConfig, get_config


class TestWorkerConfigDefaults:
    """Ensure every field has a sensible default without any env vars set."""

    def test_database_url_default(self):
        cfg = WorkerConfig()
        assert cfg.DATABASE_URL.startswith("postgresql+asyncpg://")

    def test_redis_url_default(self):
        cfg = WorkerConfig()
        assert cfg.REDIS_URL.startswith("redis://")

    def test_report_storage_path_default(self):
        cfg = WorkerConfig()
        assert cfg.REPORT_STORAGE_PATH == "/data/reports"

    def test_log_level_default(self):
        # Clear LOG_LEVEL from env (CI sets it to WARNING) to test true default
        with mock.patch.dict(os.environ, {k: v for k, v in os.environ.items() if k != "LOG_LEVEL"}, clear=True):
            cfg = WorkerConfig()
            assert cfg.LOG_LEVEL == "INFO"

    def test_max_jobs_default(self):
        cfg = WorkerConfig()
        assert cfg.MAX_JOBS == 10

    def test_job_timeout_default(self):
        cfg = WorkerConfig()
        assert cfg.JOB_TIMEOUT == 300

    def test_health_check_interval_default(self):
        cfg = WorkerConfig()
        assert cfg.HEALTH_CHECK_INTERVAL == 30


class TestWorkerConfigFromEnv:
    """WorkerConfig must pick up values from environment variables."""

    def test_database_url_from_env(self):
        with mock.patch.dict(os.environ, {"DATABASE_URL": "postgresql+asyncpg://u:p@db:5432/test"}):
            cfg = WorkerConfig()
            assert cfg.DATABASE_URL == "postgresql+asyncpg://u:p@db:5432/test"

    def test_redis_url_from_env(self):
        with mock.patch.dict(os.environ, {"REDIS_URL": "redis://redis-host:6380/1"}):
            cfg = WorkerConfig()
            assert cfg.REDIS_URL == "redis://redis-host:6380/1"

    def test_report_storage_path_from_env(self):
        with mock.patch.dict(os.environ, {"REPORT_STORAGE_PATH": "/tmp/reports"}):
            cfg = WorkerConfig()
            assert cfg.REPORT_STORAGE_PATH == "/tmp/reports"

    def test_log_level_from_env(self):
        with mock.patch.dict(os.environ, {"LOG_LEVEL": "DEBUG"}):
            cfg = WorkerConfig()
            assert cfg.LOG_LEVEL == "DEBUG"

    def test_max_jobs_from_env(self):
        with mock.patch.dict(os.environ, {"MAX_JOBS": "25"}):
            cfg = WorkerConfig()
            assert cfg.MAX_JOBS == 25

    def test_job_timeout_from_env(self):
        with mock.patch.dict(os.environ, {"JOB_TIMEOUT": "600"}):
            cfg = WorkerConfig()
            assert cfg.JOB_TIMEOUT == 600

    def test_health_check_interval_from_env(self):
        with mock.patch.dict(os.environ, {"HEALTH_CHECK_INTERVAL": "60"}):
            cfg = WorkerConfig()
            assert cfg.HEALTH_CHECK_INTERVAL == 60


class TestGetConfig:
    """get_config() returns a cached WorkerConfig instance."""

    def test_returns_worker_config(self):
        get_config.cache_clear()
        cfg = get_config()
        assert isinstance(cfg, WorkerConfig)

    def test_cache_returns_same_instance(self):
        get_config.cache_clear()
        a = get_config()
        b = get_config()
        assert a is b
