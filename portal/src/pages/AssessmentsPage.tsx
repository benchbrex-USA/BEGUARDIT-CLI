// Assessments list page
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { fetchAssessments, queryKeys } from '../api/queries';
import StatusBadge from '../components/StatusBadge';

export default function AssessmentsPage() {
  const [page, setPage] = useState(0);
  const limit = 20;

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.assessments({ offset: String(page * limit) }),
    queryFn: () => fetchAssessments(page * limit, limit),
  });

  const totalPages = Math.ceil((data?.total ?? 0) / limit);

  return (
    <div className="p-6 max-w-5xl">
      <h1 className="text-xl font-bold mb-4">Assessments</h1>

      <div className="bg-white rounded-lg border border-slate-200 shadow-sm">
        {isLoading ? (
          <p className="p-4 text-sm text-slate-500">Loading…</p>
        ) : !data?.items.length ? (
          <p className="p-4 text-sm text-slate-500">No assessments found.</p>
        ) : (
          <>
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-slate-500 uppercase border-b border-slate-200">
                  <th className="px-4 py-2">Host</th>
                  <th className="px-4 py-2">Mode</th>
                  <th className="px-4 py-2">Status</th>
                  <th className="px-4 py-2">Started</th>
                  <th className="px-4 py-2">Completed</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((a) => (
                  <tr key={a.id} className="border-b border-slate-50 hover:bg-slate-50">
                    <td className="px-4 py-2">
                      <Link to={`/assessments/${a.id}`} className="text-blue-600 hover:underline font-medium">
                        {a.hostname || a.id.slice(0, 8)}
                      </Link>
                    </td>
                    <td className="px-4 py-2 text-slate-600">{a.mode}</td>
                    <td className="px-4 py-2"><StatusBadge status={a.status} /></td>
                    <td className="px-4 py-2 text-slate-500 text-xs">{new Date(a.started_at).toLocaleString()}</td>
                    <td className="px-4 py-2 text-slate-500 text-xs">{a.completed_at ? new Date(a.completed_at).toLocaleString() : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>

            {totalPages > 1 && (
              <div className="flex items-center justify-between px-4 py-3 border-t border-slate-200 text-xs">
                <span className="text-slate-500">{data.total} total</span>
                <div className="flex gap-2">
                  <button onClick={() => setPage((p) => Math.max(0, p - 1))} disabled={page === 0}
                    className="px-2 py-1 rounded border border-slate-300 disabled:opacity-40">Prev</button>
                  <span className="py-1 text-slate-600">{page + 1} / {totalPages}</span>
                  <button onClick={() => setPage((p) => p + 1)} disabled={page >= totalPages - 1}
                    className="px-2 py-1 rounded border border-slate-300 disabled:opacity-40">Next</button>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
