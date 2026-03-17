// Dashboard — overview of recent assessments and severity breakdown
import { useQuery } from '@tanstack/react-query';
import { fetchAssessments } from '../api/queries';
import { queryKeys } from '../api/queries';
import { Link } from 'react-router-dom';
import StatusBadge from '../components/StatusBadge';

export default function DashboardPage() {
  const { data, isLoading } = useQuery({
    queryKey: queryKeys.assessments(),
    queryFn: () => fetchAssessments(0, 5),
  });

  return (
    <div className="p-6 max-w-5xl">
      <h1 className="text-xl font-bold mb-4">Dashboard</h1>

      {/* Stats cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <StatCard label="Total Assessments" value={data?.total ?? '—'} />
        <StatCard label="Completed" value={data?.items.filter((a) => a.status === 'completed').length ?? '—'} color="text-green-600" />
        <StatCard label="Running" value={data?.items.filter((a) => a.status === 'running').length ?? '—'} color="text-blue-600" />
        <StatCard label="Failed" value={data?.items.filter((a) => a.status === 'failed').length ?? '—'} color="text-red-600" />
      </div>

      {/* Recent assessments */}
      <div className="bg-white rounded-lg border border-slate-200 shadow-sm">
        <div className="px-4 py-3 border-b border-slate-200 flex justify-between items-center">
          <h2 className="font-semibold text-sm">Recent Assessments</h2>
          <Link to="/assessments" className="text-xs text-blue-600 hover:underline">View all</Link>
        </div>

        {isLoading ? (
          <p className="p-4 text-sm text-slate-500">Loading…</p>
        ) : !data?.items.length ? (
          <p className="p-4 text-sm text-slate-500">No assessments yet. Run <code>beguardit start</code> to begin.</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-slate-500 uppercase border-b border-slate-100">
                <th className="px-4 py-2">Host</th>
                <th className="px-4 py-2">Mode</th>
                <th className="px-4 py-2">Status</th>
                <th className="px-4 py-2">Started</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((a) => (
                <tr key={a.id} className="border-b border-slate-50 hover:bg-slate-50">
                  <td className="px-4 py-2">
                    <Link to={`/assessments/${a.id}`} className="text-blue-600 hover:underline">
                      {a.hostname || a.id.slice(0, 8)}
                    </Link>
                  </td>
                  <td className="px-4 py-2 text-slate-600">{a.mode}</td>
                  <td className="px-4 py-2"><StatusBadge status={a.status} /></td>
                  <td className="px-4 py-2 text-slate-500">{new Date(a.started_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

function StatCard({ label, value, color }: { label: string; value: string | number; color?: string }) {
  return (
    <div className="bg-white rounded-lg border border-slate-200 p-4 shadow-sm">
      <p className={`text-2xl font-bold ${color || 'text-slate-900'}`}>{value}</p>
      <p className="text-xs text-slate-500 mt-1">{label}</p>
    </div>
  );
}
