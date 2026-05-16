import { useState } from 'react';
import { X, UserPlus } from 'lucide-react';
import { adminUsersApi, type AdminUser } from '../../services/adminUsersApi';

interface Props {
  onClose: () => void;
  onCreated: (user: AdminUser) => void;
}

export default function CreateUserModal({ onClose, onCreated }: Props) {
  const [email, setEmail] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [isAdmin, setIsAdmin] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const user = await adminUsersApi.create({ email, username, password, is_admin: isAdmin });
      onCreated(user);
      onClose();
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      if (Array.isArray(detail)) {
        setError(detail.map((d: any) => d.msg).join('; '));
      } else {
        setError(detail || err?.message || 'Failed to create user.');
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <>
      <div className="fixed inset-0 bg-black/40 z-40" onClick={onClose} />
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <form
          onSubmit={submit}
          className="w-full max-w-md bg-white dark:bg-gray-900 rounded-2xl shadow-2xl border border-gray-200 dark:border-gray-800 overflow-hidden"
        >
          <header className="flex items-center justify-between px-5 py-3 border-b border-gray-200 dark:border-gray-800">
            <div className="flex items-center gap-2">
              <UserPlus className="w-4 h-4 text-blue-500" />
              <h3 className="text-sm font-bold text-gray-900 dark:text-gray-100">Create user</h3>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="p-1 rounded-md hover:bg-gray-100 dark:hover:bg-gray-800"
            >
              <X className="w-4 h-4" />
            </button>
          </header>

          <div className="p-5 space-y-3 text-xs">
            <Field label="Email">
              <input
                type="email"
                required
                autoComplete="off"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-2 py-1.5 rounded-md border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-100"
              />
            </Field>
            <Field label="Username">
              <input
                type="text"
                required
                minLength={3}
                maxLength={100}
                pattern="^[a-zA-Z0-9_-]+$"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full px-2 py-1.5 rounded-md border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-100"
              />
              <p className="text-[10px] text-gray-400 mt-1">3–100 chars, letters/digits/underscore/hyphen.</p>
            </Field>
            <Field label="Initial password">
              <input
                type="text"
                required
                minLength={12}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-2 py-1.5 rounded-md border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-100 font-mono"
              />
              <p className="text-[10px] text-gray-400 mt-1">
                12+ chars, must include uppercase, lowercase, and a digit.
              </p>
            </Field>
            <label className="flex items-center gap-2 pt-1">
              <input
                type="checkbox"
                checked={isAdmin}
                onChange={(e) => setIsAdmin(e.target.checked)}
              />
              <span className="text-gray-800 dark:text-gray-200">Grant admin role</span>
            </label>

            {error && (
              <div className="p-2 rounded-md bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300">
                {error}
              </div>
            )}
          </div>

          <footer className="flex justify-end gap-2 px-5 py-3 border-t border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-900/50">
            <button
              type="button"
              onClick={onClose}
              disabled={submitting}
              className="px-3 py-1.5 rounded-md text-xs font-bold uppercase tracking-wide text-gray-500 hover:text-gray-900 dark:hover:text-white"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="px-3 py-1.5 rounded-md text-xs font-bold uppercase tracking-wide bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {submitting ? 'Creating…' : 'Create user'}
            </button>
          </footer>
        </form>
      </div>
    </>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="flex flex-col gap-1">
      <span className="font-bold uppercase tracking-wider text-gray-500 dark:text-gray-400">
        {label}
      </span>
      {children}
    </label>
  );
}
