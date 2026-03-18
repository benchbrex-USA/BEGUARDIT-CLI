// Reports list page (§10.1)
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { fetchReports, queryKeys } from '../api/queries';
import StatusBadge from '../components/StatusBadge';
import { DataTable, Pagination, EmptyState, PageSpinner } from '../components/ui';
import type { Column } from '../components/ui';
import type { ReportJob } from '../types/api';

const COLUMNS: Column<ReportJob>[] = [
  { key: 'id', header: 'ID', render: (r) => <span className="font-mono text-xs">{r.id.slice(0, 8)}</span> },
  { key: 'session', header: 'Session', render: (r) => <span className="font-mono text-xs text-slate-500">{r.session_id.slice(0, 8)}</span> },
  { key: 'format', header: 'Format', render: (r) => <span className="uppercase text-xs">{r.format}</span> },
  { key: 'status', header: 'Status', render: (r) => <StatusBadge status={r.status} /> },
  {
    key: 'queued',
    header: 'Queued',
    render: (r) => <span className="text-slate-500 text-xs">{new Date(r.queued_at).toLocaleString()}</span>,
  },
  {
    key: 'download',
    header: 'Download',
    render: (r) =>
      r.status === 'completed' ? (
        <a href={`/api/v1/reports/${r.id}/download`} className="text-blue-600 hover:underline text-xs">
          Download
        </a>
      ) : r.status === 'failed' ? (
        <span className="text-red-500 text-xs" title={r.error_message || ''}>Failed</span>
      ) : (
        <span className="text-slate-400 text-xs">—</span>
      ),
  },
];

export default function ReportsPage() {
  const [page, setPage] = useState(0);
  const limit = 20;

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.reports({ offset: String(page * limit) }),
    queryFn: () => fetchReports(page * limit, limit),
    refetchInterval: 10_000, // Poll for report completion
  });

  const totalPages = Math.ceil((data?.total ?? 0) / limit);

  if (isLoading) return <PageSpinner />;

  return (
    <div className="p-6 max-w-5xl">
      <h1 className="text-xl font-bold mb-4">Reports</h1>

      <div className="bg-white rounded-lg border border-slate-200 shadow-sm">
        {data?.items.length ? (
          <>
            <DataTable columns={COLUMNS} data={data.items} rowKey={(r) => r.id} />
            <Pagination page={page} totalPages={totalPages} total={data.total} onPageChange={setPage} />
          </>
        ) : (
          <EmptyState
            icon="▤"
            title="No report jobs yet"
            description="Generate a report from an assessment detail page."
          />
        )}
      </div>
    </div>
  );
}
