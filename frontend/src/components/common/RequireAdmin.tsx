import { ShieldAlert } from 'lucide-react';
import type { AuthUser } from '../../hooks/useAuth';

interface RequireAdminProps {
  user: AuthUser | null | undefined;
  children: React.ReactNode;
}

export default function RequireAdmin({ user, children }: RequireAdminProps) {
  if (!user) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center text-gray-500 dark:text-gray-400">
        <ShieldAlert className="w-10 h-10 mb-3 text-amber-500" />
        <h3 className="text-lg font-bold text-gray-700 dark:text-gray-200">Sign in required</h3>
        <p className="text-sm mt-1">Sign in with an admin account to view this section.</p>
      </div>
    );
  }
  if (!user.is_admin) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center text-gray-500 dark:text-gray-400">
        <ShieldAlert className="w-10 h-10 mb-3 text-red-500" />
        <h3 className="text-lg font-bold text-gray-700 dark:text-gray-200">Admin access required</h3>
        <p className="text-sm mt-1">Your account does not have permission to view this section.</p>
      </div>
    );
  }
  return <>{children}</>;
}
