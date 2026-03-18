-- BeGuardit CLI — Full Database Schema (PostgreSQL 16)
-- Source: ARCH-002-2026-03-17, Section 5
-- Shared-schema multi-tenancy: every tenant-scoped table carries tenant_id.

-- Ensure UUID generation is available (Supabase has pgcrypto but may not be enabled)
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================================
-- 5.1 Tenants and Identity
-- ============================================================================

CREATE TABLE IF NOT EXISTS tenants (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(255) NOT NULL,
    slug            VARCHAR(100) NOT NULL UNIQUE,
    plan            VARCHAR(50)  NOT NULL DEFAULT 'free',
    settings        JSONB        NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           VARCHAR(320) NOT NULL UNIQUE,
    password_hash   VARCHAR(255) NOT NULL,
    display_name    VARCHAR(255),
    is_active       BOOLEAN      NOT NULL DEFAULT true,
    last_login_at   TIMESTAMPTZ,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS memberships (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID         NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tenant_id       UUID         NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    role            VARCHAR(50)  NOT NULL DEFAULT 'viewer'
                    CHECK (role IN ('admin', 'operator', 'viewer')),
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    UNIQUE (user_id, tenant_id)
);

CREATE INDEX IF NOT EXISTS idx_memberships_tenant ON memberships(tenant_id);
CREATE INDEX IF NOT EXISTS idx_memberships_user   ON memberships(user_id);

CREATE TABLE IF NOT EXISTS sessions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID         NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tenant_id       UUID         NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    token_hash      VARCHAR(255) NOT NULL UNIQUE,
    expires_at      TIMESTAMPTZ  NOT NULL,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_sessions_user   ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_expiry ON sessions(expires_at);

-- ============================================================================
-- 5.2 Assessments and Evidence
-- ============================================================================

CREATE TABLE IF NOT EXISTS assessment_sessions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID         NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    started_by      UUID         REFERENCES users(id),
    mode            VARCHAR(20)  NOT NULL CHECK (mode IN ('offline', 'online')),
    status          VARCHAR(30)  NOT NULL DEFAULT 'running'
                    CHECK (status IN ('running', 'completed', 'failed', 'cancelled')),
    scan_config     JSONB        NOT NULL DEFAULT '{}',
    hostname        VARCHAR(255),
    os_info         JSONB,
    started_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    completed_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_assess_tenant ON assessment_sessions(tenant_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_assess_status ON assessment_sessions(status);

CREATE TABLE IF NOT EXISTS assets (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id      UUID         NOT NULL REFERENCES assessment_sessions(id) ON DELETE CASCADE,
    tenant_id       UUID         NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    asset_type      VARCHAR(50)  NOT NULL,
    name            VARCHAR(500) NOT NULL,
    metadata        JSONB        NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_assets_session ON assets(session_id);
CREATE INDEX IF NOT EXISTS idx_assets_tenant  ON assets(tenant_id);

CREATE TABLE IF NOT EXISTS evidence (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id      UUID         NOT NULL REFERENCES assessment_sessions(id) ON DELETE CASCADE,
    tenant_id       UUID         NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    collector_name  VARCHAR(100) NOT NULL,
    evidence_type   VARCHAR(50)  NOT NULL,
    data            JSONB        NOT NULL,
    collected_at    TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_evidence_session ON evidence(session_id);

CREATE TABLE IF NOT EXISTS findings (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id      UUID         NOT NULL REFERENCES assessment_sessions(id) ON DELETE CASCADE,
    tenant_id       UUID         NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    rule_id         VARCHAR(100) NOT NULL,
    title           VARCHAR(500) NOT NULL,
    description     TEXT,
    severity        VARCHAR(20)  NOT NULL
                    CHECK (severity IN ('critical', 'high', 'medium', 'low', 'info')),
    category        VARCHAR(50)  NOT NULL,
    evidence_ids    UUID[]       NOT NULL DEFAULT '{}',
    remediation     TEXT,
    metadata        JSONB        NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_findings_session  ON findings(session_id);
CREATE INDEX IF NOT EXISTS idx_findings_severity ON findings(severity);
CREATE INDEX IF NOT EXISTS idx_findings_tenant   ON findings(tenant_id, created_at DESC);

-- ============================================================================
-- 5.3 Reports and Jobs
-- ============================================================================

CREATE TABLE IF NOT EXISTS report_jobs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id      UUID         NOT NULL REFERENCES assessment_sessions(id) ON DELETE CASCADE,
    tenant_id       UUID         NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    format          VARCHAR(20)  NOT NULL DEFAULT 'html'
                    CHECK (format IN ('html', 'pdf', 'sarif', 'json')),
    status          VARCHAR(30)  NOT NULL DEFAULT 'queued'
                    CHECK (status IN ('queued', 'processing', 'completed', 'failed')),
    output_path     VARCHAR(1000),
    error_message   TEXT,
    attempts        INTEGER      NOT NULL DEFAULT 0,
    queued_at       TIMESTAMPTZ  NOT NULL DEFAULT now(),
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_rjobs_status ON report_jobs(status) WHERE status IN ('queued', 'processing');
CREATE INDEX IF NOT EXISTS idx_rjobs_tenant ON report_jobs(tenant_id, queued_at DESC);

CREATE TABLE IF NOT EXISTS audit_log (
    id              BIGSERIAL PRIMARY KEY,
    tenant_id       UUID         REFERENCES tenants(id),
    user_id         UUID         REFERENCES users(id),
    action          VARCHAR(100) NOT NULL,
    resource_type   VARCHAR(100),
    resource_id     UUID,
    detail          JSONB,
    ip_address      INET,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_audit_tenant ON audit_log(tenant_id, created_at DESC);
