# Tests for src.admin.schemas — Pydantic models
# Requires Python 3.10+ for PEP 604 union syntax (str | None)
import sys
import uuid
from datetime import datetime, timezone

import pytest

if sys.version_info < (3, 10):
    pytest.skip("Admin schemas use PEP 604 union syntax requiring Python 3.10+", allow_module_level=True)

from src.admin.schemas import AdminUserOut, AuditLogOut, UpdateUserRequest


class TestAdminUserOut:
    def test_valid_user(self):
        user = AdminUserOut(
            id=uuid.uuid4(),
            email="admin@example.com",
            display_name="Admin User",
            is_active=True,
            role="admin",
            last_login_at=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc),
        )
        assert user.role == "admin"
        assert user.is_active is True

    def test_optional_fields(self):
        user = AdminUserOut(
            id=uuid.uuid4(),
            email="test@example.com",
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )
        assert user.display_name is None
        assert user.role is None
        assert user.last_login_at is None


class TestUpdateUserRequest:
    def test_all_fields(self):
        req = UpdateUserRequest(role="operator", is_active=False, display_name="New Name")
        assert req.role == "operator"
        assert req.is_active is False

    def test_role_validation(self):
        with pytest.raises(Exception):
            UpdateUserRequest(role="superadmin")

    def test_valid_roles(self):
        for role in ["admin", "operator", "viewer"]:
            req = UpdateUserRequest(role=role)
            assert req.role == role

    def test_empty_update(self):
        req = UpdateUserRequest()
        assert req.role is None
        assert req.is_active is None
        assert req.display_name is None


class TestAuditLogOut:
    def test_int_id(self):
        log = AuditLogOut(
            id=12345,
            action="user.login",
            created_at=datetime.now(timezone.utc),
        )
        assert log.id == 12345
        assert isinstance(log.id, int)

    def test_full_entry(self):
        log = AuditLogOut(
            id=1,
            user_id=uuid.uuid4(),
            action="user.update",
            resource_type="user",
            resource_id=uuid.uuid4(),
            detail={"field": "role", "new": "admin"},
            ip_address="192.168.1.1",
            created_at=datetime.now(timezone.utc),
        )
        assert log.action == "user.update"
        assert log.detail["field"] == "role"
