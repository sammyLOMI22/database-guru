import { useCallback, useEffect, useState } from 'react';
import {
  ChevronLeft,
  ChevronRight,
  Copy,
  KeyRound,
  RefreshCw,
  Search,
  ShieldAlert,
  ShieldCheck,
  UserCheck,
  UserPlus,
  UserX,
} from 'lucide-react';
import {
  adminUsersApi,
  type AdminUser,
  type AdminUserListQuery,
} from '../../services/adminUsersApi';
import CreateUserModal from './CreateUserModal';

const PAGE_SIZE = 50;

interface FilterState {
  search: string;
  is_active: '' | 'true' | 'false';
  is_admin: '' | 'true' | 'false';
}

const EMPTY_FILTERS: FilterState = { search: '', is_active: '', is_admin: '' };

interface ResetResult {
  user: AdminUser;
  password: string;
}

interface ConfirmDeactivate {
  user: AdminUser;
}

interface UserManagementProps {
  currentUserId?: number;
}

export default function UserManagement({ currentUserId }: UserManagementProps) {
  const [filters, setFilters] = useState<FilterState>(EMPTY_FILTERS);
  const [appliedFilters, setAppliedFilters] = useState<FilterState>(EMPTY_FILTERS);
  const [page, setPage] = useState(0);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [resetResult, setResetResult] = useState<ResetResult | null>(null);
  const [pendingId, setPendingId] = useState<number | null>(null);
  const [confirmDeactivate, setConfirmDeactivate] = useState<ConfirmDeactivate | null>(null);
  const [copied, setCopied] = useState(false);

  const fetchUsers = useCallback(
    async (f: FilterState, offset: number) => {
      setLoading(true);
      setError(null);
      try {
        const query: AdminUserListQuery = {
          search: f.search || undefined,
          is_active: f.is_active === '' ? undefined : f.is_active === 'true',
          is_admin: f.is_admin === '' ? undefined : f.is_admin === 'true',
          limit: PAGE_SIZE,
          offset,
        };
        const resp = await adminUsersApi.list(query);
        setUsers(resp.items);
        setTotal(resp.total);
      } catch (err: any) {
        const status = err?.response?.status;
        if (status === 403) setError('Admin access required.');
        else if (status === 401) setError('Sign in to manage users.');
        else setError(err?.message || 'Failed to load users.');
        setUsers([]);
        setTotal(0);
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  useEffect(() => {
    fetchUsers(appliedFilters, page * PAGE_SIZE);
  }, [appliedFilters, page, fetchUsers]);

  const apply = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(0);
    setAppliedFilters(filters);
  };

  const refresh = () => fetchUsers(appliedFilters, page * PAGE_SIZE);

  const updateUser = async (user: AdminUser, patch: { is_active?: boolean; is_admin?: boolean }) => {
    setPendingId(user.id);
    setError(null);
    try {
      const updated = await adminUsersApi.update(user.id, patch);
      setUsers((list) => list.map((u) => (u.id === updated.id ? updated : u)));
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || 'Update failed.');
    } finally {
      setPendingId(null);
    }
  };

  const resetPassword = async (user: AdminUser) => {
    setPendingId(user.id);
    setError(null);
    try {
      const resp = await adminUsersApi.resetPassword(user.id);
      setResetResult({ user, password: resp.temporary_password });
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || 'Reset failed.');
    } finally {
      setPendingId(null);
    }
  };

  const deactivate = async (user: AdminUser) => {
    setPendingId(user.id);
    setError(null);
    try {
      await adminUsersApi.deactivate(user.id);
      setUsers((list) => list.map((u) => (u.id === user.id ? { ...u, is_active: false } : u)));
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || 'Deactivate failed.');
    } finally {
      setPendingId(null);
      setConfirmDeactivate(null);
    }
  };

  const copyPassword = async (pw: string) => {
    try {
      await navigator.clipboard.writeText(pw);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // ignore
    }
  };

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const showingFrom = total === 0 ? 0 : page * PAGE_SIZE + 1;
  const showingTo = Math.min(total, page * PAGE_SIZE + users.length);

  return (
    <div className="max-w-[1600px] mx-auto p-6 space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <UserCheck className="w-6 h-6 text-purple-500" />
          <div>
            <h2 className="text-xl font-black tracking-tight text-gray-900 dark:text-gray-100">
              Users
            </h2>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Manage accounts, roles, and password resets.
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={refresh}
            disabled={loading}
            className="flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-bold uppercase tracking-wide bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
          <button
            onClick={() => setShowCreate(true)}
            className="flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-bold uppercase tracking-wide bg-blue-600 text-white hover:bg-blue-700"
          >
            <UserPlus className="w-3.5 h-3.5" />
            New user
          </button>
        </div>
      </div>

      <form
        onSubmit={apply}
        className="grid grid-cols-1 sm:grid-cols-4 gap-3 p-4 rounded-xl bg-white/60 dark:bg-gray-900/60 border border-gray-200 dark:border-gray-800"
      >
        <label className="flex flex-col gap-1 text-xs sm:col-span-2">
          <span className="font-bold uppercase tracking-wider text-gray-500 dark:text-gray-400">
            Search
          </span>
          <div className="relative">
            <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400" />
            <input
              type="text"
              placeholder="Username or email"
              value={filters.search}
              onChange={(e) => setFilters((f) => ({ ...f, search: e.target.value }))}
              className="w-full pl-7 pr-2 py-1.5 rounded-md border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-100"
            />
          </div>
        </label>

        <label className="flex flex-col gap-1 text-xs">
          <span className="font-bold uppercase tracking-wider text-gray-500 dark:text-gray-400">
            Status
          </span>
          <select
            value={filters.is_active}
            onChange={(e) =>
              setFilters((f) => ({ ...f, is_active: e.target.value as FilterState['is_active'] }))
            }
            className="px-2 py-1.5 rounded-md border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-100"
          >
            <option value="">All</option>
            <option value="true">Active</option>
            <option value="false">Inactive</option>
          </select>
        </label>

        <label className="flex flex-col gap-1 text-xs">
          <span className="font-bold uppercase tracking-wider text-gray-500 dark:text-gray-400">
            Role
          </span>
          <select
            value={filters.is_admin}
            onChange={(e) =>
              setFilters((f) => ({ ...f, is_admin: e.target.value as FilterState['is_admin'] }))
            }
            className="px-2 py-1.5 rounded-md border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-100"
          >
            <option value="">All</option>
            <option value="true">Admins</option>
            <option value="false">Non-admins</option>
          </select>
        </label>

        <div className="sm:col-span-4 flex justify-end">
          <button
            type="submit"
            className="px-3 py-1.5 rounded-md text-xs font-bold uppercase bg-blue-600 text-white hover:bg-blue-700"
          >
            Apply filters
          </button>
        </div>
      </form>

      {error && (
        <div className="p-3 rounded-md bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300 text-sm">
          {error}
        </div>
      )}

      <div className="rounded-xl border border-gray-200 dark:border-gray-800 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full text-xs">
            <thead className="bg-gray-100 dark:bg-gray-900 text-gray-600 dark:text-gray-300 uppercase tracking-wider">
              <tr>
                <th className="px-3 py-2 text-left">User</th>
                <th className="px-3 py-2 text-left">Email</th>
                <th className="px-3 py-2 text-left">Role</th>
                <th className="px-3 py-2 text-left">Status</th>
                <th className="px-3 py-2 text-left">Created</th>
                <th className="px-3 py-2 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
              {users.length === 0 && !loading && (
                <tr>
                  <td colSpan={6} className="px-3 py-8 text-center text-gray-400">
                    No users match the current filters.
                  </td>
                </tr>
              )}
              {users.map((u) => {
                const isSelf = currentUserId === u.id;
                const isPending = pendingId === u.id;
                return (
                  <tr key={u.id} className="hover:bg-blue-50/40 dark:hover:bg-blue-900/10">
                    <td className="px-3 py-2 text-gray-800 dark:text-gray-100">
                      <span className="font-bold">{u.username}</span>
                      <span className="ml-1 text-[10px] text-gray-400 font-mono">#{u.id}</span>
                      {isSelf && (
                        <span className="ml-2 text-[10px] font-bold uppercase text-blue-500">
                          you
                        </span>
                      )}
                    </td>
                    <td className="px-3 py-2 text-gray-700 dark:text-gray-200 font-mono">
                      {u.email}
                    </td>
                    <td className="px-3 py-2">
                      <button
                        onClick={() => updateUser(u, { is_admin: !u.is_admin })}
                        disabled={isPending || isSelf}
                        title={isSelf ? "You can't change your own role" : 'Toggle admin role'}
                        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                          u.is_admin
                            ? 'bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300'
                            : 'bg-gray-100 dark:bg-gray-800 text-gray-500'
                        } ${isPending || isSelf ? 'opacity-50 cursor-not-allowed' : 'hover:opacity-80'}`}
                      >
                        <ShieldCheck className="w-3 h-3" />
                        {u.is_admin ? 'Admin' : 'User'}
                      </button>
                    </td>
                    <td className="px-3 py-2">
                      <span
                        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                          u.is_active
                            ? 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-300'
                            : 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300'
                        }`}
                      >
                        {u.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td className="px-3 py-2 font-mono text-gray-500 dark:text-gray-400">
                      {new Date(u.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-3 py-2 text-right space-x-1">
                      <button
                        onClick={() => resetPassword(u)}
                        disabled={isPending}
                        title="Reset password"
                        className="px-2 py-1 rounded-md text-[10px] font-bold uppercase tracking-wider bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300 hover:opacity-80 disabled:opacity-50"
                      >
                        <KeyRound className="w-3 h-3 inline mr-1" />
                        Reset
                      </button>
                      {u.is_active && (
                        <button
                          onClick={() => setConfirmDeactivate({ user: u })}
                          disabled={isPending || isSelf}
                          title={isSelf ? "You can't deactivate yourself" : 'Deactivate user'}
                          className="px-2 py-1 rounded-md text-[10px] font-bold uppercase tracking-wider bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 hover:opacity-80 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          <UserX className="w-3 h-3 inline mr-1" />
                          Disable
                        </button>
                      )}
                      {!u.is_active && (
                        <button
                          onClick={() => updateUser(u, { is_active: true })}
                          disabled={isPending}
                          title="Reactivate user"
                          className="px-2 py-1 rounded-md text-[10px] font-bold uppercase tracking-wider bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-300 hover:opacity-80 disabled:opacity-50"
                        >
                          <UserCheck className="w-3 h-3 inline mr-1" />
                          Enable
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
        <span>
          {loading
            ? 'Loading…'
            : total === 0
              ? 'No results'
              : `Showing ${showingFrom}–${showingTo} of ${total}`}
        </span>
        <div className="flex items-center gap-1">
          <button
            onClick={() => setPage((p) => Math.max(0, p - 1))}
            disabled={page === 0 || loading}
            className="p-1 rounded-md hover:bg-gray-100 dark:hover:bg-gray-800 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
          <span className="px-2 font-mono">
            {page + 1} / {totalPages}
          </span>
          <button
            onClick={() => setPage((p) => (p + 1 < totalPages ? p + 1 : p))}
            disabled={page + 1 >= totalPages || loading}
            className="p-1 rounded-md hover:bg-gray-100 dark:hover:bg-gray-800 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      </div>

      {showCreate && (
        <CreateUserModal
          onClose={() => setShowCreate(false)}
          onCreated={(user) => {
            setUsers((list) => [user, ...list]);
            setTotal((t) => t + 1);
          }}
        />
      )}

      {resetResult && (
        <>
          <div className="fixed inset-0 bg-black/40 z-40" onClick={() => setResetResult(null)} />
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <div className="w-full max-w-md bg-white dark:bg-gray-900 rounded-2xl shadow-2xl border border-gray-200 dark:border-gray-800 overflow-hidden">
              <header className="px-5 py-3 border-b border-gray-200 dark:border-gray-800 flex items-center gap-2">
                <KeyRound className="w-4 h-4 text-amber-500" />
                <h3 className="text-sm font-bold text-gray-900 dark:text-gray-100">
                  Temporary password for {resetResult.user.username}
                </h3>
              </header>
              <div className="p-5 space-y-3 text-xs">
                <p className="text-gray-600 dark:text-gray-300">
                  Share this securely. The user should change it on next login. This is the only
                  time it will be shown.
                </p>
                <div className="flex items-center gap-2">
                  <code className="flex-1 px-3 py-2 rounded-md bg-gray-100 dark:bg-gray-800 font-mono text-sm break-all text-gray-800 dark:text-gray-100">
                    {resetResult.password}
                  </code>
                  <button
                    onClick={() => copyPassword(resetResult.password)}
                    className="flex items-center gap-1 px-2 py-1.5 rounded-md bg-blue-600 text-white text-[10px] font-bold uppercase tracking-wider"
                  >
                    <Copy className="w-3 h-3" />
                    {copied ? 'Copied' : 'Copy'}
                  </button>
                </div>
              </div>
              <footer className="px-5 py-3 border-t border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-900/50 flex justify-end">
                <button
                  onClick={() => setResetResult(null)}
                  className="px-3 py-1.5 rounded-md text-xs font-bold uppercase tracking-wide bg-gray-200 dark:bg-gray-800 text-gray-700 dark:text-gray-200"
                >
                  Done
                </button>
              </footer>
            </div>
          </div>
        </>
      )}

      {confirmDeactivate && (
        <>
          <div
            className="fixed inset-0 bg-black/40 z-40"
            onClick={() => setConfirmDeactivate(null)}
          />
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <div className="w-full max-w-sm bg-white dark:bg-gray-900 rounded-2xl shadow-2xl border border-gray-200 dark:border-gray-800 overflow-hidden">
              <header className="px-5 py-3 border-b border-gray-200 dark:border-gray-800 flex items-center gap-2">
                <ShieldAlert className="w-4 h-4 text-red-500" />
                <h3 className="text-sm font-bold text-gray-900 dark:text-gray-100">
                  Deactivate {confirmDeactivate.user.username}?
                </h3>
              </header>
              <div className="p-5 text-xs text-gray-600 dark:text-gray-300">
                The user will be unable to log in until reactivated. Their data is preserved.
              </div>
              <footer className="px-5 py-3 border-t border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-900/50 flex justify-end gap-2">
                <button
                  onClick={() => setConfirmDeactivate(null)}
                  className="px-3 py-1.5 rounded-md text-xs font-bold uppercase tracking-wide text-gray-500 hover:text-gray-900 dark:hover:text-white"
                >
                  Cancel
                </button>
                <button
                  onClick={() => deactivate(confirmDeactivate.user)}
                  disabled={pendingId === confirmDeactivate.user.id}
                  className="px-3 py-1.5 rounded-md text-xs font-bold uppercase tracking-wide bg-red-600 text-white hover:bg-red-700 disabled:opacity-50"
                >
                  Deactivate
                </button>
              </footer>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
