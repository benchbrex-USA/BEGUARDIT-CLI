// Shell layout — sidebar nav + main content area (§10.1)
// Uses Zustand authStore instead of React Context.
import { type ReactNode } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAuthStore } from '../stores/authStore';
import { useUiStore } from '../stores/uiStore';

const NAV_ITEMS = [
  { to: '/', label: 'Dashboard', icon: '◉' },
  { to: '/assessments', label: 'Assessments', icon: '⬡' },
  { to: '/reports', label: 'Reports', icon: '▤' },
  { to: '/upload', label: 'Upload', icon: '▲' },
  { to: '/settings', label: 'Settings', icon: '⚙' },
];

const ADMIN_ITEMS = [
  { to: '/admin/users', label: 'Users', icon: '⊕' },
  { to: '/admin/audit-log', label: 'Audit Log', icon: '⊙' },
  { to: '/admin/tenants', label: 'Tenant Settings', icon: '⊞' },
];

export default function Layout({ children }: { children: ReactNode }) {
  const user = useAuthStore((s) => s.user);
  const role = useAuthStore((s) => s.role);
  const logout = useAuthStore((s) => s.logout);
  const sidebarCollapsed = useUiStore((s) => s.sidebarCollapsed);
  const toggleSidebar = useUiStore((s) => s.toggleSidebar);
  const location = useLocation();

  const isAdmin = role === 'admin';

  const isActive = (to: string) =>
    location.pathname === to || (to !== '/' && location.pathname.startsWith(to));

  const navLink = (item: { to: string; label: string; icon: string }) => (
    <Link
      key={item.to}
      to={item.to}
      className={`flex items-center gap-2 px-3 py-2 rounded-md text-sm transition-colors ${
        isActive(item.to) ? 'bg-blue-600 text-white' : 'hover:bg-slate-800 hover:text-white'
      }`}
    >
      <span className="text-base">{item.icon}</span>
      {!sidebarCollapsed && item.label}
    </Link>
  );

  return (
    <div className="flex h-screen">
      {/* Sidebar */}
      <aside className={`${sidebarCollapsed ? 'w-14' : 'w-56'} bg-slate-900 text-slate-300 flex flex-col transition-all duration-200`}>
        <div className="p-4 border-b border-slate-700 flex items-center justify-between">
          {!sidebarCollapsed && (
            <div>
              <h1 className="text-lg font-bold text-white tracking-tight">BeGuardit</h1>
              <p className="text-xs text-slate-500 mt-0.5">Security Portal</p>
            </div>
          )}
          <button
            onClick={toggleSidebar}
            className="text-slate-500 hover:text-white text-xs"
            title={sidebarCollapsed ? 'Expand' : 'Collapse'}
          >
            {sidebarCollapsed ? '»' : '«'}
          </button>
        </div>

        <nav className="flex-1 p-2 space-y-0.5">
          {NAV_ITEMS.map(navLink)}

          {isAdmin && (
            <>
              {!sidebarCollapsed && (
                <p className="px-3 pt-4 pb-1 text-[10px] uppercase text-slate-600 tracking-wider">Admin</p>
              )}
              {ADMIN_ITEMS.map(navLink)}
            </>
          )}
        </nav>

        <div className="p-3 border-t border-slate-700 text-xs">
          {!sidebarCollapsed && (
            <>
              <p className="text-slate-400 truncate">{user?.email}</p>
              <p className="text-slate-500">{role}</p>
            </>
          )}
          <button
            onClick={() => void logout()}
            className="mt-2 text-slate-500 hover:text-red-400 transition-colors"
          >
            {sidebarCollapsed ? '↪' : 'Sign out'}
          </button>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 overflow-auto bg-slate-50">
        {children}
      </main>
    </div>
  );
}
