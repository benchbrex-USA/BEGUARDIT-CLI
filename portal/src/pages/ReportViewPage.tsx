// Single report view page (§10.1 — /reports/:id)
import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { fetchReport, queryKeys } from '../api/queries';
import StatusBadge from '../components/StatusBadge';
import { Button, Card, PageSpinner, Spinner } from '../components/ui';

export default function ReportViewPage() {
  const { id } = useParams<{ id: string }>();

  const { data: report, isLoading, error } = useQuery({
    queryKey: queryKeys.report(id!),
    queryFn: () => fetchReport(id!),
    enabled: !!id,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      // Poll while the report is still being generated
      return status === 'queued' || status === 'processing' ? 3_000 : false;
    },
  });

  if (isLoading) return <PageSpinner />;

  if (error || !report) {
    return (
      <div className="p-6 max-w-3xl">
        <Link to="/reports" className="text-blue-600 hover:underline text-xs mb-4 inline-block">&larr; Back to Reports</Link>
        <Card>
          <div className="text-center py-8">
            <p className="text-sm text-red-600 font-medium mb-1">Failed to load report</p>
            <p className="text-xs text-slate-500">{(error as Error)?.message || 'Report not found.'}</p>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-5xl">
      <Link to="/reports" className="text-blue-600 hover:underline text-xs mb-4 inline-block">&larr; Back to Reports</Link>

      <div className="flex items-center gap-3 mb-4">
        <h1 className="text-xl font-bold">Report</h1>
        <StatusBadge status={report.status} />
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4 text-xs">
        <Card>
          <p className="text-slate-500">ID</p>
          <p className="font-mono mt-0.5">{report.id.slice(0, 8)}</p>
        </Card>
        <Card>
          <p className="text-slate-500">Session</p>
          <p className="font-mono mt-0.5">{report.session_id.slice(0, 8)}</p>
        </Card>
        <Card>
          <p className="text-slate-500">Format</p>
          <p className="uppercase mt-0.5">{report.format}</p>
        </Card>
        <Card>
          <p className="text-slate-500">Queued</p>
          <p className="mt-0.5">{new Date(report.queued_at).toLocaleString()}</p>
        </Card>
      </div>

      {/* Completed — render report */}
      {report.status === 'completed' && (
        <Card padding={false} className="overflow-hidden">
          <div className="flex items-center justify-between px-4 py-2 border-b border-slate-200 bg-slate-50">
            <span className="text-xs text-slate-500">Report Preview</span>
            <a href={`/api/v1/reports/${report.id}/download`} download>
              <Button variant="secondary" size="sm">Download</Button>
            </a>
          </div>
          <iframe
            src={`/api/v1/reports/${report.id}/download`}
            title="Report preview"
            className="w-full border-0"
            style={{ minHeight: '70vh' }}
            sandbox="allow-same-origin"
          />
        </Card>
      )}

      {/* Queued / Processing — spinner */}
      {(report.status === 'queued' || report.status === 'processing') && (
        <Card>
          <div className="flex flex-col items-center justify-center py-12 gap-3">
            <Spinner size="lg" />
            <p className="text-sm text-slate-600 font-medium">
              {report.status === 'queued' ? 'Report is queued for generation...' : 'Report is being generated...'}
            </p>
            <p className="text-xs text-slate-400">This page will update automatically.</p>
          </div>
        </Card>
      )}

      {/* Failed */}
      {report.status === 'failed' && (
        <Card>
          <div className="text-center py-8">
            <p className="text-sm text-red-600 font-medium mb-1">Report generation failed</p>
            <p className="text-xs text-slate-500">{report.error_message || 'An unknown error occurred.'}</p>
            {report.attempts > 1 && (
              <p className="text-xs text-slate-400 mt-1">Attempts: {report.attempts}</p>
            )}
          </div>
        </Card>
      )}
    </div>
  );
}
