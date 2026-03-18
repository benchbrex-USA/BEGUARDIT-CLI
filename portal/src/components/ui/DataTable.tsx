// Component library — DataTable (§10.3)
import type { ReactNode } from 'react';

export interface Column<T> {
  key: string;
  header: string;
  render: (row: T) => ReactNode;
  className?: string;
}

interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  rowKey: (row: T) => string;
  emptyMessage?: string;
}

export default function DataTable<T>({ columns, data, rowKey, emptyMessage = 'No data.' }: DataTableProps<T>) {
  if (!data.length) {
    return <p className="p-4 text-sm text-slate-500">{emptyMessage}</p>;
  }

  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="text-left text-xs text-slate-500 uppercase border-b border-slate-200">
          {columns.map((col) => (
            <th key={col.key} className={`px-4 py-2 ${col.className || ''}`}>
              {col.header}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {data.map((row) => (
          <tr key={rowKey(row)} className="border-b border-slate-50 hover:bg-slate-50">
            {columns.map((col) => (
              <td key={col.key} className={`px-4 py-2 ${col.className || ''}`}>
                {col.render(row)}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
