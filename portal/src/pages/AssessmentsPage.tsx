// Assessments list page (§10.1)
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { fetchAssessments, queryKeys } from '../api/queries';
import StatusBadge from '../components/StatusBadge';
import { DataTable, Pagination, EmptyState, TableSkeleton, ErrorCard } from '../components/ui';
import type { Column } from '../components/ui';
import type { AssessmentSummary } from '../types/api';

const COLUMNS: Column<AssessmentSummary>[] = [
  {
    key: 'host',
    header: 'Host',
    render: (a) => (
      <Link to={`/assessments/${a.id}`} className="text-blue-600 hover:underline font-medium">
        {a.hostname || a.id.slice(0, 8)}
      </Link>
    ),
  },
  { key: 'mode', header: 'Mode', render: (a) => <span className="text-slate-600">{a.mode}</span> },
  { key: 'status', header: 'Status', render: (a) => <StatusBadge status={a.status} /> },
  {
    key: 'started',
    header: 'Started',
    render: (a) => <span className="text-slate-500 text-xs">{new Date(a.started_at).toLocaleString()}</span>,
  },
  {
    key: 'completed',
    header: 'Completed',
    render: (a) => (
      <span className="text-slate-500 text-xs">
        {a.completed_at ? new Date(a.completed_at).toLocaleString() : '—'}
      </span>
    ),
  },
];

export default function AssessmentsPage() {
  const [page, setPage] = useState(0);
  const limit = 20;

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: queryKeys.assessments({ offset: String(page * limit) }),
    queryFn: () => fetchAssessments(page * limit, limit),
  });

  const totalPages = Math.ceil((data?.total ?? 0) / limit);

  if (isLoading) {
    return (
      <div className="p-6 max-w-5xl">
        <h1 className="text-xl font-bold mb-4">Assessments</h1>
        <TableSkeleton rows={8} columns={5} />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 max-w-5xl">
        <h1 className="text-xl font-bold mb-4">Assessments</h1>
        <ErrorCard message={error instanceof Error ? error.message : 'Failed to load assessments'} onRetry={refetch} />
      </div>
    );
  }

  return (
    <div className="p-6 max-w-5xl">
      <h1 className="text-xl font-bold mb-4">Assessments</h1>

      <div className="bg-white rounded-lg border border-slate-200 shadow-sm">
        {data?.items.length ? (
          <>
            <DataTable columns={COLUMNS} data={data.items} rowKey={(a) => a.id} />
            <Pagination page={page} totalPages={totalPages} total={data.total} onPageChange={setPage} />
          </>
        ) : (
          <EmptyState icon="⬡" title="No assessments found" />
        )}
      </div>
    </div>
  );
}
