// Settings page — tenant info, member management
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fetchTenant, fetchMembers, inviteMember, removeMember, updateMemberRole, queryKeys } from '../api/queries';
import { useAuth } from '../context/AuthContext';
import { useState, type FormEvent } from 'react';

export default function SettingsPage() {
  const { role } = useAuth();
  const qc = useQueryClient();
  const isAdmin = role === 'admin';

  const { data: tenant } = useQuery({ queryKey: queryKeys.tenant, queryFn: fetchTenant });
  const { data: members } = useQuery({ queryKey: queryKeys.members, queryFn: fetchMembers });

  // Invite form
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRole, setInviteRole] = useState('viewer');
  const [inviteError, setInviteError] = useState('');

  const inviteMut = useMutation({
    mutationFn: () => inviteMember(inviteEmail, inviteRole),
    onSuccess: () => { setInviteEmail(''); qc.invalidateQueries({ queryKey: queryKeys.members }); },
    onError: (err: Error) => setInviteError(err.message),
  });

  const removeMut = useMutation({
    mutationFn: (id: string) => removeMember(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.members }),
  });

  const roleMut = useMutation({
    mutationFn: ({ id, role }: { id: string; role: string }) => updateMemberRole(id, role),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.members }),
  });

  const handleInvite = (e: FormEvent) => {
    e.preventDefault();
    setInviteError('');
    inviteMut.mutate();
  };

  return (
    <div className="p-6 max-w-3xl">
      <h1 className="text-xl font-bold mb-4">Settings</h1>

      {/* Tenant info */}
      {tenant && (
        <div className="bg-white border border-slate-200 rounded-lg p-4 mb-6 shadow-sm">
          <h2 className="font-semibold text-sm mb-2">Organization</h2>
          <dl className="grid grid-cols-2 gap-2 text-sm">
            <dt className="text-slate-500">Name</dt><dd>{tenant.name}</dd>
            <dt className="text-slate-500">Slug</dt><dd className="font-mono">{tenant.slug}</dd>
            <dt className="text-slate-500">Plan</dt><dd className="capitalize">{tenant.plan}</dd>
          </dl>
        </div>
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
                <td className="px-4 py-2">{m.email}</td>
                <td className="px-4 py-2">
                  {isAdmin ? (
                    <select value={m.role} onChange={(e) => roleMut.mutate({ id: m.id, role: e.target.value })}
                      className="text-xs border border-slate-300 rounded px-1 py-0.5">
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
                    <button onClick={() => removeMut.mutate(m.id)}
                      className="text-xs text-red-600 hover:underline">Remove</button>
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>

        {/* Invite form */}
        {isAdmin && (
          <form onSubmit={handleInvite} className="px-4 py-3 border-t border-slate-200 flex gap-2 items-end">
            <div className="flex-1">
              <label className="block text-xs text-slate-500 mb-1">Invite by email</label>
              <input type="email" required value={inviteEmail} onChange={(e) => setInviteEmail(e.target.value)}
                className="w-full px-2 py-1.5 border border-slate-300 rounded text-sm outline-none focus:ring-1 focus:ring-blue-500" />
            </div>
            <select value={inviteRole} onChange={(e) => setInviteRole(e.target.value)}
              className="px-2 py-1.5 border border-slate-300 rounded text-sm">
              <option value="viewer">viewer</option>
              <option value="operator">operator</option>
              <option value="admin">admin</option>
            </select>
            <button type="submit" disabled={inviteMut.isPending}
              className="px-3 py-1.5 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 disabled:opacity-50">
              Invite
            </button>
            {inviteError && <span className="text-xs text-red-600">{inviteError}</span>}
          </form>
        )}
      </div>
    </div>
  );
}
