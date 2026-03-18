// Shared API types matching backend schemas

export interface User {
  id: string;
  email: string;
  display_name: string | null;
  is_active: boolean;
  last_login_at: string | null;
  created_at: string;
}

export interface Membership {
  tenant_id: string;
  tenant_name: string;
  tenant_slug: string;
  role: 'admin' | 'operator' | 'viewer';
}

export interface MeResponse {
  user: User;
  current_tenant_id: string;
  current_role: string;
  memberships: Membership[];
}

export interface AuthResponse {
  user: User;
  tenant_id: string;
  role: string;
}

export interface Tenant {
  id: string;
  name: string;
  slug: string;
  plan: string;
  settings: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface Member {
  id: string;
  user_id: string;
  email: string;
  display_name: string | null;
  role: string;
  created_at: string;
}

export interface AssessmentSummary {
  id: string;
  mode: string;
  status: string;
  hostname: string | null;
  scan_config: Record<string, unknown>;
  started_at: string;
  completed_at: string | null;
  created_at: string;
}

export interface AssessmentDetail extends AssessmentSummary {
  started_by: string | null;
  os_info: Record<string, unknown> | null;
  finding_count: number;
  asset_count: number;
  evidence_count: number;
  severity_summary: Record<string, number>;
}

export interface Finding {
  id: string;
  session_id: string;
  rule_id: string;
  title: string;
  description: string | null;
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info';
  category: string;
  evidence_ids: string[];
  remediation: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface Asset {
  id: string;
  session_id: string;
  asset_type: string;
  name: string;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface ReportJob {
  id: string;
  session_id: string;
  format: string;
  status: 'queued' | 'processing' | 'completed' | 'failed';
  output_path: string | null;
  error_message: string | null;
  attempts: number;
  queued_at: string;
  started_at: string | null;
  completed_at: string | null;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  offset: number;
  limit: number;
}

export interface ApiError {
  error: {
    code: string;
    message: string;
    detail: unknown;
    correlation_id?: string;
  };
}

// Admin types (§6.6)

export interface AdminUser {
  id: string;
  email: string;
  display_name: string | null;
  is_active: boolean;
  role: string | null;
  last_login_at: string | null;
  created_at: string;
}

export interface AuditLogEntry {
  id: string;
  user_id: string | null;
  action: string;
  resource_type: string | null;
  resource_id: string | null;
  detail: Record<string, unknown> | null;
  ip_address: string | null;
  created_at: string;
}

// Upload types (§6.4)

export interface UploadResponse {
  session_id: string;
  findings_imported: number;
  assets_imported: number;
  evidence_imported: number;
}
