// Assessment detail page — summary, findings, assets
import { useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { fetchAssessment, fetchFindings, fetchAssets, queryKeys } from '../api/queries';
import StatusBadge from '../components/StatusBadge';
import SeverityBadge from '../components/SeverityBadge';

export default function AssessmentDetailPage() {
  const { id } = useParams<{ id: string }>();

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

  if (isLoading) return <div className="p-6 text-sm text-slate-500">Loading…</div>;
  if (!assessment) return <div className="p-6 text-sm text-red-600">Assessment not found.</div>;

  const sev = assessment.severity_summary || {};

  return (
    <div className="p-6 max-w-5xl">
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div>
          <h1 className="text-xl font-bold">{assessment.hostname || 'Assessment'}</h1>
          <p className="text-xs text-slate-500 font-mono mt-0.5">{assessment.id}</p>
        </div>
        <StatusBadge status={assessment.status} />
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-6">
        <SevCard label="Critical" count={sev.critical ?? 0} color="text-red-600" />
        <SevCard label="High" count={sev.high ?? 0} color="text-orange-600" />
        <SevCard label="Medium" count={sev.medium ?? 0} color="text-amber-600" />
        <SevCard label="Low" count={sev.low ?? 0} color="text-blue-600" />
        <SevCard label="Info" count={sev.info ?? 0} color="text-gray-500" />
      </div>

      <div className="grid grid-cols-3 gap-3 mb-6">
        <MetaCard label="Mode" value={assessment.mode} />
        <MetaCard label="Assets" value={assessment.asset_count} />
        <MetaCard label="Evidence" value={assessment.evidence_count} />
      </div>

      {/* Findings */}
      <h2 className="font-semibold text-sm mb-2">Findings ({assessment.finding_count})</h2>
      <div className="space-y-2 mb-6">
        {findingsData?.items.map((f) => (
          <div key={f.id} className="bg-white border border-slate-200 rounded-lg p-3">
            <div className="flex items-center gap-2 mb-1">
              <SeverityBadge severity={f.severity} />
              <span className="text-xs text-slate-500 font-mono">{f.rule_id}</span>
              <span className="font-medium text-sm">{f.title}</span>
            </div>
            {f.description && <p className="text-xs text-slate-600 mt-1">{f.description}</p>}
            {f.remediation && <p className="text-xs text-green-700 mt-1">{f.remediation}</p>}
          </div>
        ))}
        {!findingsData?.items.length && <p className="text-sm text-slate-500">No findings.</p>}
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
      </div>
    </div>
  );
}

function SevCard({ label, count, color }: { label: string; count: number; color: string }) {
  return (
    <div className="bg-white border border-slate-200 rounded-lg p-3 text-center shadow-sm">
      <p className={`text-xl font-bold ${color}`}>{count}</p>
      <p className="text-xs text-slate-500">{label}</p>
    </div>
  );
}

function MetaCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="bg-white border border-slate-200 rounded-lg p-3 shadow-sm">
      <p className="text-xs text-slate-500">{label}</p>
      <p className="font-medium text-sm">{value}</p>
    </div>
  );
}
