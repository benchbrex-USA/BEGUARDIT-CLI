// Dashboard — overview of recent assessments and severity breakdown (§10.1)
import { useQuery } from '@tanstack/react-query';
import { fetchAssessments, queryKeys } from '../api/queries';
import { Link } from 'react-router-dom';
import StatusBadge from '../components/StatusBadge';
import { StatCard, DataTable, EmptyState, PageSpinner } from '../components/ui';
import type { Column } from '../components/ui';
import type { AssessmentSummary } from '../types/api';

const COLUMNS: Column<AssessmentSummary>[] = [
  {
    key: 'host',
    header: 'Host',
    render: (a) => (
      <Link to={`/assessments/${a.id}`} className="text-blue-600 hover:underline">
        {a.hostname || a.id.slice(0, 8)}
      </Link>
    ),
  },
  { key: 'mode', header: 'Mode', render: (a) => <span className="text-slate-600">{a.mode}</span> },
  { key: 'status', header: 'Status', render: (a) => <StatusBadge status={a.status} /> },
  { key: 'started', header: 'Started', render: (a) => <span className="text-slate-500">{new Date(a.started_at).toLocaleString()}</span> },
];

export default function DashboardPage() {
  const { data, isLoading } = useQuery({
    queryKey: queryKeys.assessments(),
    queryFn: () => fetchAssessments(0, 5),
  });

  if (isLoading) return <PageSpinner />;

  const items = data?.items ?? [];

  return (
    <div className="p-6 max-w-5xl">
      <h1 className="text-xl font-bold mb-4">Dashboard</h1>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <StatCard label="Total Assessments" value={data?.total ?? '—'} />
        <StatCard label="Completed" value={items.filter((a) => a.status === 'completed').length} color="text-green-600" />
        <StatCard label="Running" value={items.filter((a) => a.status === 'running').length} color="text-blue-600" />
        <StatCard label="Failed" value={items.filter((a) => a.status === 'failed').length} color="text-red-600" />
      </div>

      <div className="bg-white rounded-lg border border-slate-200 shadow-sm">
        <div className="px-4 py-3 border-b border-slate-200 flex justify-between items-center">
          <h2 className="font-semibold text-sm">Recent Assessments</h2>
          <Link to="/assessments" className="text-xs text-blue-600 hover:underline">View all</Link>
        </div>

        {items.length ? (
          <DataTable columns={COLUMNS} data={items} rowKey={(a) => a.id} />
        ) : (
          <EmptyState
            icon="⬡"
            title="No assessments yet"
            description="Run beguardit start from the CLI to begin your first security assessment."
          />
        )}
      </div>
    </div>
  );
}
