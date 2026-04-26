import { useState } from 'react';
import { AlertCircle, CheckCircle2, Eye, EyeOff, KeyRound, LogOut } from 'lucide-react';
import api, { type AuthTokenResponse } from '../services/api';
import mascot from '../assets/boxer_mascot.png';

interface PasswordResetProps {
  token: string;
  onSuccess: (resp: AuthTokenResponse) => void;
  onCancel: () => void;
}

export default function PasswordReset({ token, onSuccess, onCancel }: PasswordResetProps) {
  const [newPassword, setNewPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [show, setShow] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (newPassword !== confirm) {
      setError('New password and confirmation do not match.');
      return;
    }
    setSubmitting(true);
    try {
      const { data } = await api.post<AuthTokenResponse>('/api/auth/redeem-reset', {
        token,
        new_password: newPassword,
      });
      onSuccess(data);
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      if (typeof detail === 'string') setError(detail);
      else if (Array.isArray(detail)) setError(detail.map((d: any) => d.msg).join('. '));
      else setError('Could not redeem reset link.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 via-white to-purple-50 dark:from-gray-950 dark:via-gray-900 dark:to-blue-950 transition-colors duration-500">
      <div className="w-full max-w-md mx-4 animate-fadeIn">
        <div className="flex flex-col items-center mb-8">
          <div className="w-20 h-20 mb-4 animate-float">
            <img src={mascot} alt="Database Guru" className="w-full h-full object-contain drop-shadow-xl" />
          </div>
          <h1 className="text-2xl font-black tracking-tight text-gradient">Database Guru</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">Set a new password</p>
        </div>

        <div className="glass-panel rounded-2xl p-8 shadow-xl border border-white/20 dark:border-white/5">
          <div className="flex items-center gap-2 mb-2">
            <KeyRound className="w-5 h-5 text-amber-500" />
            <h2 className="text-lg font-bold text-gray-900 dark:text-white">
              Redeem reset link
            </h2>
          </div>
          <p className="text-sm text-gray-600 dark:text-gray-300 mb-5 flex items-start gap-2">
            <CheckCircle2 className="w-4 h-4 mt-0.5 text-emerald-500 flex-shrink-0" />
            <span>Enter your new password below. The link is single-use.</span>
          </p>

          {error && (
            <div className="flex items-start gap-2 p-3 mb-4 rounded-xl bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800/30 text-red-700 dark:text-red-400 text-sm animate-fadeIn">
              <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={submit} className="space-y-4">
            <div>
              <label className="block text-xs font-bold text-gray-500 dark:text-gray-400 mb-1 uppercase tracking-wider">
                New password
              </label>
              <div className="relative">
                <input
                  type={show ? 'text' : 'password'}
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  className="w-full px-3 py-2 pr-9 rounded-lg border border-gray-200 dark:border-gray-700 bg-white/60 dark:bg-gray-900/60 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                  minLength={12}
                  autoFocus
                  autoComplete="new-password"
                />
                <button
                  type="button"
                  onClick={() => setShow((v) => !v)}
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                >
                  {show ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              <p className="text-[10px] mt-1 text-gray-500 dark:text-gray-400">
                12+ characters with upper, lower, and a digit.
              </p>
            </div>

            <div>
              <label className="block text-xs font-bold text-gray-500 dark:text-gray-400 mb-1 uppercase tracking-wider">
                Confirm new password
              </label>
              <input
                type={show ? 'text' : 'password'}
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white/60 dark:bg-gray-900/60 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                required
                minLength={12}
                autoComplete="new-password"
              />
            </div>

            <button
              type="submit"
              disabled={submitting}
              className="w-full py-2.5 rounded-lg bg-blue-600 hover:bg-blue-700 disabled:opacity-60 disabled:cursor-not-allowed text-white text-sm font-bold tracking-wide transition-colors"
            >
              {submitting ? 'Redeeming…' : 'Set password and sign in'}
            </button>
          </form>

          <button
            type="button"
            onClick={onCancel}
            className="mt-4 w-full flex items-center justify-center gap-1.5 text-xs text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
          >
            <LogOut className="w-3 h-3" />
            Skip for now
          </button>
        </div>
      </div>
    </div>
  );
}
