// Severity badge — color-coded label
const COLORS: Record<string, string> = {
  critical: 'bg-red-100 text-red-700 border-red-200',
  high: 'bg-orange-100 text-orange-700 border-orange-200',
  medium: 'bg-amber-100 text-amber-700 border-amber-200',
  low: 'bg-blue-100 text-blue-700 border-blue-200',
  info: 'bg-gray-100 text-gray-600 border-gray-200',
};

export default function SeverityBadge({ severity }: { severity: string }) {
  const cls = COLORS[severity] || COLORS.info;
  return (
    <span className={`inline-block px-2 py-0.5 text-xs font-semibold uppercase rounded border ${cls}`}>
      {severity}
    </span>
  );
}
