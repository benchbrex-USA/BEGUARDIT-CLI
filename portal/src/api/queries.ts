// TanStack Query keys and query functions
import { api } from './client';
import type {
  AssessmentDetail,
  AssessmentSummary,
  AuthResponse,
  Finding,
  Asset,
  MeResponse,
  Member,
  PaginatedResponse,
  ReportJob,
  Tenant,
} from '../types/api';

// ── Query keys ──────────────────────────────────────────────────────

export const queryKeys = {
  me: ['me'] as const,
  tenant: ['tenant'] as const,
  members: ['members'] as const,
  assessments: (params?: Record<string, string>) => ['assessments', params] as const,
  assessment: (id: string) => ['assessment', id] as const,
  findings: (id: string, params?: Record<string, string>) => ['findings', id, params] as const,
  assets: (id: string) => ['assets', id] as const,
  reports: (params?: Record<string, string>) => ['reports', params] as const,
  report: (id: string) => ['report', id] as const,
};

// ── Auth ─────────────────────────────────────────────────────────────

export const fetchMe = () => api.get<MeResponse>('/auth/me');

export const login = (email: string, password: string) =>
  api.post<AuthResponse>('/auth/login', { email, password });

export const register = (data: {
  email: string;
  password: string;
  display_name?: string;
  tenant_name: string;
  tenant_slug: string;
}) => api.post<AuthResponse>('/auth/register', data);

export const logout = () => api.post('/auth/logout');

export const switchTenant = (tenant_id: string) =>
  api.post<AuthResponse>('/auth/switch-tenant', { tenant_id });

// ── Tenant ───────────────────────────────────────────────────────────

export const fetchTenant = () => api.get<Tenant>('/tenants/');

export const fetchMembers = () => api.get<Member[]>('/tenants/members');

export const inviteMember = (email: string, role: string) =>
  api.post<Member>('/tenants/members', { email, role });

export const updateMemberRole = (memberId: string, role: string) =>
  api.patch<Member>(`/tenants/members/${memberId}`, { role });

export const removeMember = (memberId: string) =>
  api.delete(`/tenants/members/${memberId}`);

// ── Assessments ──────────────────────────────────────────────────────

export const fetchAssessments = (offset = 0, limit = 20, status?: string) => {
  const params = new URLSearchParams({ offset: String(offset), limit: String(limit) });
  if (status) params.set('status', status);
  return api.get<PaginatedResponse<AssessmentSummary>>(`/assessments/?${params}`);
};

export const fetchAssessment = (id: string) =>
  api.get<AssessmentDetail>(`/assessments/${id}`);

export const fetchFindings = (id: string, offset = 0, limit = 50, severity?: string) => {
  const params = new URLSearchParams({ offset: String(offset), limit: String(limit) });
  if (severity) params.set('severity', severity);
  return api.get<PaginatedResponse<Finding>>(`/assessments/${id}/findings?${params}`);
};

export const fetchAssets = (id: string, offset = 0, limit = 50) =>
  api.get<PaginatedResponse<Asset>>(`/assessments/${id}/assets?offset=${offset}&limit=${limit}`);

export const deleteAssessment = (id: string) =>
  api.delete(`/assessments/${id}`);

// ── Reports ──────────────────────────────────────────────────────────

export const fetchReports = (offset = 0, limit = 20, sessionId?: string) => {
  const params = new URLSearchParams({ offset: String(offset), limit: String(limit) });
  if (sessionId) params.set('session_id', sessionId);
  return api.get<PaginatedResponse<ReportJob>>(`/reports/?${params}`);
};

export const fetchReport = (id: string) => api.get<ReportJob>(`/reports/${id}`);

export const createReport = (sessionId: string, format: string) =>
  api.post<ReportJob>('/reports/', { session_id: sessionId, format });
