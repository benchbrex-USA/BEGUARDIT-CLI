# Tenants domain — re-exports from auth.models
# Source: ARCH-002-2026-03-17, Section 5
#
# The canonical Tenant and Membership ORM models live in auth.models
# because they are tightly coupled to the auth flow (registration creates
# a tenant, sessions reference tenant_id).  This module re-exports them
# so that tenant-domain code can import from its own package.
from src.auth.models import Membership, Tenant

__all__ = ["Tenant", "Membership"]
