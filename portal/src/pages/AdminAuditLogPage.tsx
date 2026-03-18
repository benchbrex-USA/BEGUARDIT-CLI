// Admin — audit log page (§10.1 / §6.6)
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { fetchAuditLog, queryKeys } from '../api/queries';
import { DataTable, Pagination, PageSpinner, EmptyState } from '../components/ui';
import type { Column } from '../components/ui';
import type { AuditLogEntry } from '../types/api';

const COLUMNS: Column<AuditLogEntry>[] = [
  {
    key: 'time',
    header: 'Time',
    render: (e) => <span className="text-xs text-slate-500">{new Date(e.created_at).toLocaleString()}</span>,
  },
  {
    key: 'action',
    header: 'Action',
    render: (e) => (
      <span className="text-xs px-2 py-0.5 rounded bg-slate-100 text-slate-700 font-mono">{e.action}</span>
    ),
  },
  {
    key: 'user',
    header: 'User ID',
    render: (e) => (
      <span className="text-xs text-slate-500 font-mono">{e.user_id?.slice(0, 8) || '—'}</span>
    ),
  },
  {
    key: 'resource',
    header: 'Resource',
    render: (e) => (
      <span className="text-xs text-slate-600">
        {e.resource_type ? `${e.resource_type}/${e.resource_id?.slice(0, 8)}` : '—'}
      </span>
    ),
  },
  {
    key: 'ip',
    header: 'IP',
    render: (e) => <span className="text-xs text-slate-500 font-mono">{e.ip_address || '—'}</span>,
  },
  {
    key: 'detail',
    header: 'Detail',
    render: (e) => (
      <span className="text-xs text-slate-500 truncate max-w-[200px] inline-block">
        {e.detail ? JSON.stringify(e.detail) : '—'}
      </span>
    ),
  },
];

export default function AdminAuditLogPage() {
  const [page, setPage] = useState(0);
  const [actionFilter, setActionFilter] = useState('');
  const limit = 50;

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.auditLog({ offset: String(page * limit), action: actionFilter }),
    queryFn: () => fetchAuditLog(page * limit, limit, actionFilter || undefined),
  });

  const totalPages = Math.ceil((data?.total ?? 0) / limit);

  if (isLoading) return <PageSpinner />;

  return (
    <div className="p-6 max-w-6xl">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-xl font-bold">Audit Log</h1>
        <input
          type="text"
          placeholder="Filter by action…"
          value={actionFilter}
          onChange={(e) => { setActionFilter(e.target.value); setPage(0); }}
          className="px-3 py-1.5 border border-slate-300 rounded-md text-sm w-48 outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      <div className="bg-white rounded-lg border border-slate-200 shadow-sm">
        {data?.items.length ? (
          <>
            <DataTable columns={COLUMNS} data={data.items} rowKey={(e) => e.id} />
            <Pagination page={page} totalPages={totalPages} total={data.total} onPageChange={setPage} />
          </>
        ) : (
          <EmptyState icon="⊙" title="No audit entries" description="Actions will appear here as users interact with the system." />
        )}
      </div>
    </div>
  );
}
