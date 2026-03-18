// Admin — user management page (§10.1 / §6.6)
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fetchAdminUsers, updateAdminUser, queryKeys } from '../api/queries';
import { useUiStore } from '../stores/uiStore';
import { DataTable, Pagination, PageSpinner, EmptyState, Button, Modal, Input } from '../components/ui';
import type { Column } from '../components/ui';
import type { AdminUser } from '../types/api';

export default function AdminUsersPage() {
  const qc = useQueryClient();
  const addToast = useUiStore((s) => s.addToast);
  const [page, setPage] = useState(0);
  const limit = 50;

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.adminUsers({ offset: String(page * limit) }),
    queryFn: () => fetchAdminUsers(page * limit, limit),
  });

  // Edit modal state
  const [editing, setEditing] = useState<AdminUser | null>(null);
  const [editRole, setEditRole] = useState('');
  const [editActive, setEditActive] = useState(true);
  const [editName, setEditName] = useState('');

  const openEdit = (user: AdminUser) => {
    setEditing(user);
    setEditRole(user.role || 'viewer');
    setEditActive(user.is_active);
    setEditName(user.display_name || '');
  };

  const editMut = useMutation({
    mutationFn: () =>
      updateAdminUser(editing!.id, {
        role: editRole,
        is_active: editActive,
        display_name: editName || undefined,
      }),
    onSuccess: () => {
      setEditing(null);
      qc.invalidateQueries({ queryKey: ['adminUsers'] });
      addToast({ type: 'success', message: 'User updated.' });
    },
    onError: (err: Error) => addToast({ type: 'error', message: err.message }),
  });

  const totalPages = Math.ceil((data?.total ?? 0) / limit);

  const columns: Column<AdminUser>[] = [
    { key: 'email', header: 'Email', render: (u) => <span className="font-medium">{u.email}</span> },
    { key: 'name', header: 'Name', render: (u) => <span className="text-slate-600 text-xs">{u.display_name || '—'}</span> },
    {
      key: 'role',
      header: 'Role',
      render: (u) => (
        <span className="text-xs px-2 py-0.5 rounded bg-slate-100 text-slate-700">{u.role || '—'}</span>
      ),
    },
    {
      key: 'active',
      header: 'Active',
      render: (u) => (
        <span className={`text-xs font-medium ${u.is_active ? 'text-green-600' : 'text-red-500'}`}>
          {u.is_active ? 'Yes' : 'No'}
        </span>
      ),
    },
    {
      key: 'login',
      header: 'Last Login',
      render: (u) => (
        <span className="text-slate-500 text-xs">
          {u.last_login_at ? new Date(u.last_login_at).toLocaleString() : 'Never'}
        </span>
      ),
    },
    {
      key: 'actions',
      header: '',
      render: (u) => (
        <Button variant="ghost" size="sm" onClick={() => openEdit(u)}>
          Edit
        </Button>
      ),
    },
  ];

  if (isLoading) return <PageSpinner />;

  return (
    <div className="p-6 max-w-5xl">
      <h1 className="text-xl font-bold mb-4">User Management</h1>

      <div className="bg-white rounded-lg border border-slate-200 shadow-sm">
        {data?.items.length ? (
          <>
            <DataTable columns={columns} data={data.items} rowKey={(u) => u.id} />
            <Pagination page={page} totalPages={totalPages} total={data.total} onPageChange={setPage} />
          </>
        ) : (
          <EmptyState icon="⊕" title="No users found" />
        )}
      </div>

      {/* Edit modal */}
      <Modal
        open={!!editing}
        onClose={() => setEditing(null)}
        title={`Edit User — ${editing?.email}`}
        footer={
          <>
            <Button variant="secondary" size="sm" onClick={() => setEditing(null)}>Cancel</Button>
            <Button size="sm" loading={editMut.isPending} onClick={() => editMut.mutate()}>Save</Button>
          </>
        }
      >
        <div className="space-y-4">
          <Input label="Display Name" value={editName} onChange={(e) => setEditName(e.target.value)} />

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Role</label>
            <select
              value={editRole}
              onChange={(e) => setEditRole(e.target.value)}
              className="w-full px-3 py-2 border border-slate-300 rounded-md text-sm"
            >
              <option value="admin">admin</option>
              <option value="operator">operator</option>
              <option value="viewer">viewer</option>
            </select>
          </div>

          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="active-toggle"
              checked={editActive}
              onChange={(e) => setEditActive(e.target.checked)}
              className="rounded border-slate-300"
            />
            <label htmlFor="active-toggle" className="text-sm text-slate-700">Active</label>
          </div>
        </div>
      </Modal>
    </div>
  );
}
