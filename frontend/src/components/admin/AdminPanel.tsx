import { useState } from 'react';
import { ScrollText, HeartPulse, Users } from 'lucide-react';
import AuditLogViewer from './AuditLogViewer';
import UserManagement from './UserManagement';
import SystemHealthPanel from './SystemHealthPanel';

type AdminSubTab = 'users' | 'audit' | 'health';

const SUB_TABS: { id: AdminSubTab; label: string; icon: React.ReactNode }[] = [
  { id: 'users', label: 'Users', icon: <Users className="w-3.5 h-3.5" /> },
  { id: 'audit', label: 'Audit Log', icon: <ScrollText className="w-3.5 h-3.5" /> },
  { id: 'health', label: 'Health', icon: <HeartPulse className="w-3.5 h-3.5" /> },
];

interface AdminPanelProps {
  currentUserId?: number;
}

export default function AdminPanel({ currentUserId }: AdminPanelProps) {
  const [tab, setTab] = useState<AdminSubTab>('users');

  return (
    <div className="flex flex-col h-full">
      <nav className="px-6 pt-6 flex items-center gap-2 border-b border-gray-200 dark:border-gray-800">
        {SUB_TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`flex items-center gap-2 px-4 py-2 rounded-t-lg text-xs font-bold uppercase tracking-wide transition-colors ${
              tab === t.id
                ? 'bg-blue-600 text-white'
                : 'text-gray-500 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-800'
            }`}
          >
            {t.icon}
            {t.label}
          </button>
        ))}
      </nav>

      <div className="flex-1 overflow-auto">
        {tab === 'users' && <UserManagement currentUserId={currentUserId} />}
        {tab === 'audit' && <AuditLogViewer />}
        {tab === 'health' && <SystemHealthPanel />}
      </div>
    </div>
  );
}
