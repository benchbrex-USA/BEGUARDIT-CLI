// Assessment detail page — summary, findings, assets (§10.1)
import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fetchAssessment, fetchFindings, fetchAssets, deleteAssessment, createReport, queryKeys } from '../api/queries';
import { useAuthStore } from '../stores/authStore';
import { useUiStore } from '../stores/uiStore';
import StatusBadge from '../components/StatusBadge';
import SeverityBadge from '../components/SeverityBadge';
import { Button, Modal, PageSpinner, EmptyState, StatCard } from '../components/ui';

export default function AssessmentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const role = useAuthStore((s) => s.role);
  const addToast = useUiStore((s) => s.addToast);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [reportFormat, setReportFormat] = useState('html');

  const { data: assessment, isLoading } = useQuery({
    queryKey: queryKeys.assessment(id!),
    queryFn: () => fetchAssessment(id!),
    enabled: !!id,
  });

  const { data: findingsData } = useQuery({
    queryKey: queryKeys.findings(id!),
    queryFn: () => fetchFindings(id!),
    enabled: !!id,
  });

  const { data: assetsData } = useQuery({
    queryKey: queryKeys.assets(id!),
    queryFn: () => fetchAssets(id!),
    enabled: !!id,
  });

  const deleteMut = useMutation({
    mutationFn: () => deleteAssessment(id!),
    onSuccess: () => {
      addToast({ type: 'success', message: 'Assessment deleted.' });
      qc.invalidateQueries({ queryKey: ['assessments'] });
      navigate('/assessments');
    },
    onError: (err: Error) => addToast({ type: 'error', message: err.message }),
  });

  const reportMut = useMutation({
    mutationFn: () => createReport(id!, reportFormat),
    onSuccess: () => {
      addToast({ type: 'success', message: `${reportFormat.toUpperCase()} report queued.` });
      qc.invalidateQueries({ queryKey: ['reports'] });
    },
    onError: (err: Error) => addToast({ type: 'error', message: err.message }),
  });

  if (isLoading) return <PageSpinner />;
  if (!assessment) return <div className="p-6 text-sm text-red-600">Assessment not found.</div>;

  const sev = assessment.severity_summary || {};
  const canDelete = role === 'admin' || role === 'operator';

  return (
    <div className="p-6 max-w-5xl">
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div>
          <h1 className="text-xl font-bold">{assessment.hostname || 'Assessment'}</h1>
          <p className="text-xs text-slate-500 font-mono mt-0.5">{assessment.id}</p>
        </div>
        <div className="flex items-center gap-2">
          <StatusBadge status={assessment.status} />
          {canDelete && (
            <Button variant="danger" size="sm" onClick={() => setDeleteOpen(true)}>
              Delete
            </Button>
          )}
        </div>
      </div>

      {/* Severity cards */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-6">
        <StatCard label="Critical" value={sev.critical ?? 0} color="text-red-600" />
        <StatCard label="High" value={sev.high ?? 0} color="text-orange-600" />
        <StatCard label="Medium" value={sev.medium ?? 0} color="text-amber-600" />
        <StatCard label="Low" value={sev.low ?? 0} color="text-blue-600" />
        <StatCard label="Info" value={sev.info ?? 0} color="text-gray-500" />
      </div>

      {/* Meta */}
      <div className="grid grid-cols-3 gap-3 mb-6">
        <StatCard label="Mode" value={assessment.mode} />
        <StatCard label="Assets" value={assessment.asset_count} />
        <StatCard label="Evidence" value={assessment.evidence_count} />
      </div>

      {/* Generate report */}
      <div className="flex items-center gap-2 mb-6">
        <select
          value={reportFormat}
          onChange={(e) => setReportFormat(e.target.value)}
          className="text-sm border border-slate-300 rounded-md px-2 py-1.5"
        >
          <option value="html">HTML</option>
          <option value="pdf">PDF</option>
          <option value="sarif">SARIF</option>
        </select>
        <Button size="sm" variant="secondary" loading={reportMut.isPending} onClick={() => reportMut.mutate()}>
          Generate Report
        </Button>
      </div>

      {/* Findings */}
      <h2 className="font-semibold text-sm mb-2">Findings ({assessment.finding_count})</h2>
      <div className="space-y-2 mb-6">
        {findingsData?.items.length ? (
          findingsData.items.map((f) => (
            <div key={f.id} className="bg-white border border-slate-200 rounded-lg p-3">
              <div className="flex items-center gap-2 mb-1">
                <SeverityBadge severity={f.severity} />
                <span className="text-xs text-slate-500 font-mono">{f.rule_id}</span>
                <span className="font-medium text-sm">{f.title}</span>
              </div>
              {f.description && <p className="text-xs text-slate-600 mt-1">{f.description}</p>}
              {f.remediation && <p className="text-xs text-green-700 mt-1">{f.remediation}</p>}
            </div>
          ))
        ) : (
          <EmptyState title="No findings" icon="✓" />
        )}
      </div>

      {/* Assets */}
      <h2 className="font-semibold text-sm mb-2">Assets ({assessment.asset_count})</h2>
      <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-slate-500 uppercase border-b border-slate-200">
              <th className="px-4 py-2">Type</th>
              <th className="px-4 py-2">Name</th>
            </tr>
          </thead>
          <tbody>
            {assetsData?.items.slice(0, 50).map((a) => (
              <tr key={a.id} className="border-b border-slate-50">
                <td className="px-4 py-1.5 text-slate-600 text-xs">{a.asset_type}</td>
                <td className="px-4 py-1.5 font-mono text-xs">{a.name}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {!assetsData?.items.length && (
          <p className="p-4 text-sm text-slate-500">No assets discovered.</p>
        )}
      </div>

      {/* Delete modal */}
      <Modal
        open={deleteOpen}
        onClose={() => setDeleteOpen(false)}
        title="Delete Assessment"
        footer={
          <>
            <Button variant="secondary" size="sm" onClick={() => setDeleteOpen(false)}>Cancel</Button>
            <Button variant="danger" size="sm" loading={deleteMut.isPending} onClick={() => deleteMut.mutate()}>Delete</Button>
          </>
        }
      >
        <p className="text-sm text-slate-600">
          This will permanently delete this assessment and all associated findings, assets, and evidence.
          This action cannot be undone.
        </p>
      </Modal>
    </div>
  );
}
