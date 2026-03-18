// Settings page — tenant info, member management (§10.1)
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fetchTenant, fetchMembers, inviteMember, removeMember, updateMemberRole, queryKeys } from '../api/queries';
import { useAuthStore } from '../stores/authStore';
import { useUiStore } from '../stores/uiStore';
import { useState, type FormEvent } from 'react';
import { Button, Input, Card } from '../components/ui';

export default function SettingsPage() {
  const role = useAuthStore((s) => s.role);
  const memberships = useAuthStore((s) => s.memberships);
  const switchTenant = useAuthStore((s) => s.switchTenant);
  const addToast = useUiStore((s) => s.addToast);
  const qc = useQueryClient();
  const isAdmin = role === 'admin';

  const { data: tenant } = useQuery({ queryKey: queryKeys.tenant, queryFn: fetchTenant });
  const { data: members } = useQuery({ queryKey: queryKeys.members, queryFn: fetchMembers });

  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRole, setInviteRole] = useState('viewer');

  const inviteMut = useMutation({
    mutationFn: () => inviteMember(inviteEmail, inviteRole),
    onSuccess: () => {
      setInviteEmail('');
      qc.invalidateQueries({ queryKey: queryKeys.members });
      addToast({ type: 'success', message: 'Member invited.' });
    },
    onError: (err: Error) => addToast({ type: 'error', message: err.message }),
  });

  const removeMut = useMutation({
    mutationFn: (id: string) => removeMember(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.members });
      addToast({ type: 'success', message: 'Member removed.' });
    },
  });

  const roleMut = useMutation({
    mutationFn: ({ id, role }: { id: string; role: string }) => updateMemberRole(id, role),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.members });
      addToast({ type: 'success', message: 'Role updated.' });
    },
  });

  const handleInvite = (e: FormEvent) => {
    e.preventDefault();
    inviteMut.mutate();
  };

  return (
    <div className="p-6 max-w-3xl">
      <h1 className="text-xl font-bold mb-4">Settings</h1>

      {/* Tenant info */}
      {tenant && (
        <Card className="mb-6">
          <h2 className="font-semibold text-sm mb-2">Organization</h2>
          <dl className="grid grid-cols-2 gap-2 text-sm">
            <dt className="text-slate-500">Name</dt><dd>{tenant.name}</dd>
            <dt className="text-slate-500">Slug</dt><dd className="font-mono">{tenant.slug}</dd>
            <dt className="text-slate-500">Plan</dt><dd className="capitalize">{tenant.plan}</dd>
          </dl>
        </Card>
      )}

      {/* Tenant switcher */}
      {memberships.length > 1 && (
        <Card className="mb-6">
          <h2 className="font-semibold text-sm mb-2">Switch Organization</h2>
          <div className="flex flex-wrap gap-2">
            {memberships.map((m) => (
              <button
                key={m.tenant_id}
                onClick={() => void switchTenant(m.tenant_id)}
                className={`px-3 py-1.5 text-xs rounded-md border transition-colors ${
                  m.tenant_id === tenant?.id
                    ? 'bg-blue-600 text-white border-blue-600'
                    : 'border-slate-300 hover:bg-slate-50'
                }`}
              >
                {m.tenant_name}
              </button>
            ))}
          </div>
        </Card>
      )}

      {/* Members */}
      <div className="bg-white border border-slate-200 rounded-lg shadow-sm">
        <div className="px-4 py-3 border-b border-slate-200">
          <h2 className="font-semibold text-sm">Members</h2>
        </div>

        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-slate-500 uppercase border-b border-slate-100">
              <th className="px-4 py-2">Email</th>
              <th className="px-4 py-2">Role</th>
              {isAdmin && <th className="px-4 py-2">Actions</th>}
            </tr>
          </thead>
          <tbody>
            {members?.map((m) => (
              <tr key={m.id} className="border-b border-slate-50">
                <td className="px-4 py-2">
                  {m.email}
                  {m.display_name && <span className="text-slate-400 ml-1 text-xs">({m.display_name})</span>}
                </td>
                <td className="px-4 py-2">
                  {isAdmin ? (
                    <select
                      value={m.role}
                      onChange={(e) => roleMut.mutate({ id: m.id, role: e.target.value })}
                      className="text-xs border border-slate-300 rounded px-1 py-0.5"
                    >
                      <option value="admin">admin</option>
                      <option value="operator">operator</option>
                      <option value="viewer">viewer</option>
                    </select>
                  ) : (
                    <span className="text-xs">{m.role}</span>
                  )}
                </td>
                {isAdmin && (
                  <td className="px-4 py-2">
                    <button
                      onClick={() => removeMut.mutate(m.id)}
                      className="text-xs text-red-600 hover:underline"
                    >
                      Remove
                    </button>
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>

        {isAdmin && (
          <form onSubmit={handleInvite} className="px-4 py-3 border-t border-slate-200 flex gap-2 items-end">
            <div className="flex-1">
              <Input
                label="Invite by email"
                type="email"
                required
                value={inviteEmail}
                onChange={(e) => setInviteEmail(e.target.value)}
              />
            </div>
            <select
              value={inviteRole}
              onChange={(e) => setInviteRole(e.target.value)}
              className="px-2 py-2 border border-slate-300 rounded text-sm"
            >
              <option value="viewer">viewer</option>
              <option value="operator">operator</option>
              <option value="admin">admin</option>
            </select>
            <Button size="sm" loading={inviteMut.isPending}>
              Invite
            </Button>
          </form>
        )}
      </div>
    </div>
  );
}
