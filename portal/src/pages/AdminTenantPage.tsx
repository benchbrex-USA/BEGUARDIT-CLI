// Admin tenant settings and member management page (§10.1 — /admin/tenants)
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  fetchTenant,
  fetchMembers,
  inviteMember,
  updateMemberRole,
  removeMember,
  queryKeys,
} from '../api/queries';
import { Button, Card, CardHeader, CardTitle, DataTable, Modal, Input, Select, PageSpinner } from '../components/ui';
import type { Column } from '../components/ui';
import type { Member } from '../types/api';

// ── Member table columns ────────────────────────────────────────────

const MEMBER_COLUMNS: Column<Member>[] = [
  {
    key: 'email',
    header: 'Email',
    render: (m) => <span className="text-sm">{m.email}</span>,
  },
  {
    key: 'display_name',
    header: 'Name',
    render: (m) => <span className="text-sm text-slate-600">{m.display_name || '—'}</span>,
  },
  {
    key: 'role',
    header: 'Role',
    render: (m) => (
      <span className="inline-block px-2 py-0.5 text-xs font-semibold rounded bg-slate-100 text-slate-700">
        {m.role}
      </span>
    ),
  },
  {
    key: 'created_at',
    header: 'Joined',
    render: (m) => <span className="text-xs text-slate-500">{new Date(m.created_at).toLocaleDateString()}</span>,
  },
];

// ── Page component ──────────────────────────────────────────────────

export default function AdminTenantPage() {
  const queryClient = useQueryClient();
  const [inviteOpen, setInviteOpen] = useState(false);
  const [editMember, setEditMember] = useState<Member | null>(null);
  const [confirmRemove, setConfirmRemove] = useState<Member | null>(null);

  // Invite form state
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRole, setInviteRole] = useState('viewer');

  // Edit role form state
  const [editRole, setEditRole] = useState('');

  const { data: tenant, isLoading: tenantLoading } = useQuery({
    queryKey: queryKeys.tenant,
    queryFn: fetchTenant,
  });

  const { data: members, isLoading: membersLoading } = useQuery({
    queryKey: queryKeys.members,
    queryFn: fetchMembers,
  });

  const inviteMut = useMutation({
    mutationFn: () => inviteMember(inviteEmail, inviteRole),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.members });
      setInviteOpen(false);
      setInviteEmail('');
      setInviteRole('viewer');
    },
  });

  const updateRoleMut = useMutation({
    mutationFn: () => updateMemberRole(editMember!.id, editRole),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.members });
      setEditMember(null);
    },
  });

  const removeMut = useMutation({
    mutationFn: () => removeMember(confirmRemove!.id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.members });
      setConfirmRemove(null);
    },
  });

  if (tenantLoading || membersLoading) return <PageSpinner />;

  // Extend columns with actions
  const columnsWithActions: Column<Member>[] = [
    ...MEMBER_COLUMNS,
    {
      key: 'actions',
      header: '',
      render: (m) => (
        <div className="flex gap-1 justify-end">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              setEditMember(m);
              setEditRole(m.role);
            }}
          >
            Edit
          </Button>
          <Button
            variant="ghost"
            size="sm"
            className="text-red-600 hover:text-red-700"
            onClick={() => setConfirmRemove(m)}
          >
            Remove
          </Button>
        </div>
      ),
    },
  ];

  return (
    <div className="p-6 max-w-5xl">
      <h1 className="text-xl font-bold mb-4">Tenant Settings</h1>

      {/* Tenant info */}
      {tenant && (
        <Card className="mb-6">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs">
            <div>
              <p className="text-slate-500">Name</p>
              <p className="font-medium mt-0.5">{tenant.name}</p>
            </div>
            <div>
              <p className="text-slate-500">Slug</p>
              <p className="font-mono mt-0.5">{tenant.slug}</p>
            </div>
            <div>
              <p className="text-slate-500">Plan</p>
              <p className="uppercase mt-0.5">{tenant.plan}</p>
            </div>
            <div>
              <p className="text-slate-500">Created</p>
              <p className="mt-0.5">{new Date(tenant.created_at).toLocaleDateString()}</p>
            </div>
          </div>
          {tenant.settings && Object.keys(tenant.settings).length > 0 && (
            <div className="mt-4 pt-3 border-t border-slate-200">
              <p className="text-xs text-slate-500 mb-1">Settings</p>
              <pre className="text-xs bg-slate-50 rounded p-2 overflow-x-auto">
                {JSON.stringify(tenant.settings, null, 2)}
              </pre>
            </div>
          )}
        </Card>
      )}

      {/* Members */}
      <div className="bg-white rounded-lg border border-slate-200 shadow-sm">
        <CardHeader className="flex items-center justify-between">
          <CardTitle>Members</CardTitle>
          <Button variant="primary" size="sm" onClick={() => setInviteOpen(true)}>
            Invite Member
          </Button>
        </CardHeader>

        {members && members.length > 0 ? (
          <DataTable columns={columnsWithActions} data={members} rowKey={(m) => m.id} />
        ) : (
          <p className="p-4 text-sm text-slate-500">No members found.</p>
        )}
      </div>

      {/* Invite modal */}
      <Modal
        open={inviteOpen}
        onClose={() => setInviteOpen(false)}
        title="Invite Member"
        footer={
          <>
            <Button variant="secondary" size="sm" onClick={() => setInviteOpen(false)}>Cancel</Button>
            <Button
              variant="primary"
              size="sm"
              loading={inviteMut.isPending}
              disabled={!inviteEmail}
              onClick={() => inviteMut.mutate()}
            >
              Send Invite
            </Button>
          </>
        }
      >
        <div className="space-y-3">
          <Input
            label="Email"
            type="email"
            value={inviteEmail}
            onChange={(e) => setInviteEmail(e.target.value)}
            placeholder="user@example.com"
          />
          <Select
            label="Role"
            value={inviteRole}
            onChange={(e) => setInviteRole(e.target.value)}
            options={[
              { value: 'viewer', label: 'Viewer' },
              { value: 'operator', label: 'Operator' },
              { value: 'admin', label: 'Admin' },
            ]}
          />
          {inviteMut.isError && (
            <p className="text-xs text-red-600">{(inviteMut.error as Error).message}</p>
          )}
        </div>
      </Modal>

      {/* Edit role modal */}
      <Modal
        open={!!editMember}
        onClose={() => setEditMember(null)}
        title="Change Role"
        footer={
          <>
            <Button variant="secondary" size="sm" onClick={() => setEditMember(null)}>Cancel</Button>
            <Button
              variant="primary"
              size="sm"
              loading={updateRoleMut.isPending}
              onClick={() => updateRoleMut.mutate()}
            >
              Update Role
            </Button>
          </>
        }
      >
        <div className="space-y-3">
          <p className="text-sm text-slate-600">{editMember?.email}</p>
          <Select
            label="Role"
            value={editRole}
            onChange={(e) => setEditRole(e.target.value)}
            options={[
              { value: 'viewer', label: 'Viewer' },
              { value: 'operator', label: 'Operator' },
              { value: 'admin', label: 'Admin' },
            ]}
          />
          {updateRoleMut.isError && (
            <p className="text-xs text-red-600">{(updateRoleMut.error as Error).message}</p>
          )}
        </div>
      </Modal>

      {/* Confirm remove modal */}
      <Modal
        open={!!confirmRemove}
        onClose={() => setConfirmRemove(null)}
        title="Remove Member"
        footer={
          <>
            <Button variant="secondary" size="sm" onClick={() => setConfirmRemove(null)}>Cancel</Button>
            <Button
              variant="danger"
              size="sm"
              loading={removeMut.isPending}
              onClick={() => removeMut.mutate()}
            >
              Remove
            </Button>
          </>
        }
      >
        <p className="text-sm text-slate-600">
          Are you sure you want to remove <strong>{confirmRemove?.email}</strong> from this tenant?
          This action cannot be undone.
        </p>
        {removeMut.isError && (
          <p className="text-xs text-red-600 mt-2">{(removeMut.error as Error).message}</p>
        )}
      </Modal>
    </div>
  );
}
