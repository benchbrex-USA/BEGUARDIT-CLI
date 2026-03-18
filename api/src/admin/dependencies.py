# Admin domain — FastAPI dependencies
# Source: ARCH-002-2026-03-17, Section 6.6
#
# All admin endpoints require the "admin" role.
from __future__ import annotations

from src.auth.dependencies import require_role

# Re-export for convenience — admin endpoints use this as a dependency
require_admin = require_role("admin")
