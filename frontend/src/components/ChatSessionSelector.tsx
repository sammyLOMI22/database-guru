import { useState, useEffect } from 'react';
import { chatAPI, connectionsAPI } from '../services/api';
import type { ChatSession, DatabaseConnection, ConnectionInfo } from '../types/api';

interface ChatSessionSelectorProps {
  currentSession: ChatSession | null;
  onSessionChange: (session: ChatSession | null) => void;
}

function RotatingConnection({ connections }: { connections: ConnectionInfo[] }) {
  const [index, setIndex] = useState(0);

  useEffect(() => {
    if (connections.length <= 1) return;
    const interval = setInterval(() => {
      setIndex((prev) => (prev + 1) % connections.length);
    }, 3000);
    return () => clearInterval(interval);
  }, [connections.length]);

  if (connections.length === 0) return <span>No DBs</span>;

  return (
    <span className="animate-fadeIn inline-block" key={index}>
      {connections[index].name}
    </span>
  );
}

export default function ChatSessionSelector({ currentSession, onSessionChange }: ChatSessionSelectorProps) {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [showCreateModal, setShowCreateModal] = useState(false);

  useEffect(() => {
    loadSessions();
  }, []);

  const loadSessions = async () => {
    try {
      const data = await chatAPI.listSessions();
      setSessions(data);
    } catch (error) {
      console.error('Failed to load chat sessions:', error);
    }
  };

  const handleDeleteSession = async (sessionId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm('Are you sure you want to delete this chat session?')) return;

    try {
      await chatAPI.deleteSession(sessionId);
      if (currentSession?.id === sessionId) {
        onSessionChange(null);
      }
      await loadSessions();
    } catch (error) {
      console.error('Failed to delete session:', error);
    }
  };

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between mb-4 px-1">
        <h3 className="text-[10px] font-black uppercase tracking-[0.2em] text-gray-400 dark:text-gray-500">Sessions</h3>
        <button
          onClick={() => setShowCreateModal(true)}
          className="px-3 py-1 text-[10px] font-black uppercase tracking-widest bg-blue-600 text-white rounded-lg hover:bg-blue-700 hover:scale-105 active:scale-95 transition-all shadow-lg shadow-blue-500/20"
        >
          + New
        </button>
      </div>

      <div className="space-y-2 custom-scrollbar">
        {/* Default session */}
        <button
          onClick={() => onSessionChange(null)}
          className={`w-full text-left p-3 rounded-xl transition-all duration-300 border ${!currentSession
            ? 'glass-card border-blue-500/30 bg-blue-500/5 text-blue-600 dark:text-blue-400 font-bold shadow-md shadow-blue-500/5'
            : 'border-transparent text-gray-600 dark:text-gray-400 hover:bg-white/5 hover:border-white/10'
            }`}
        >
          <div className="flex items-center gap-3">
            <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${!currentSession ? 'bg-blue-500/10' : 'bg-gray-100 dark:bg-gray-800'}`}>
              <span className="text-base">🚀</span>
            </div>
            <div>
              <p className="text-xs font-black uppercase tracking-wider">Default Query</p>
              <p className="text-[10px] opacity-60 font-bold uppercase tracking-tight">Global Context</p>
            </div>
          </div>
        </button>

        {/* Chat sessions */}
        {sessions.map((session) => (
          <div
            key={session.id}
            className={`group rounded-xl transition-all duration-300 border ${currentSession?.id === session.id
              ? 'glass-card border-indigo-500/30 bg-indigo-500/5 shadow-md shadow-indigo-500/5'
              : 'border-transparent hover:bg-white/5 hover:border-white/10'
              }`}
          >
            <div className="flex items-stretch">
              <button
                onClick={() => onSessionChange(session)}
                className="flex-1 text-left p-3"
              >
                <div className="flex items-center gap-3">
                  <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${currentSession?.id === session.id ? 'bg-indigo-500/10' : 'bg-gray-100 dark:bg-gray-800'}`}>
                    <span className="text-base font-bold text-gray-600 dark:text-gray-400">
                      {session.name.charAt(0).toUpperCase()}
                    </span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className={`text-xs font-black uppercase tracking-wider truncate mb-0.5 ${currentSession?.id === session.id ? 'text-indigo-600 dark:text-indigo-400' : 'text-gray-700 dark:text-gray-300'}`}>
                      {session.name}
                    </p>
                    <div className="flex items-center gap-2 opacity-60 overflow-hidden whitespace-nowrap">
                      <div className="flex items-center gap-1.5 text-[9px] font-black uppercase tracking-widest text-gray-500 dark:text-gray-400">
                        <div className="flex items-center gap-1 bg-white/10 dark:bg-black/20 px-1.5 py-0.5 rounded-md border border-white/5">
                          <span className="text-blue-500">{session.connections.length}</span>
                          <span>DBs</span>
                        </div>
                        <span className="opacity-30">•</span>
                        <div className="text-gray-600 dark:text-gray-300 flex-1 truncate">
                          <RotatingConnection connections={session.connections} />
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </button>
              <button
                onClick={(e) => handleDeleteSession(session.id, e)}
                className="opacity-0 group-hover:opacity-100 px-3 flex items-center justify-center text-red-500/50 hover:text-red-500 transition-all"
                title="Delete session"
              >
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              </button>
            </div>
          </div>
        ))}
      </div>

      {showCreateModal && (
        <CreateSessionModal
          onClose={() => setShowCreateModal(false)}
          onCreated={(session) => {
            onSessionChange(session);
            loadSessions();
            setShowCreateModal(false);
          }}
        />
      )}
    </div>
  );
}

interface CreateSessionModalProps {
  onClose: () => void;
  onCreated: (session: ChatSession) => void;
}

function CreateSessionModal({ onClose, onCreated }: CreateSessionModalProps) {
  const [name, setName] = useState('');
  const [connections, setConnections] = useState<DatabaseConnection[]>([]);
  const [selectedConnections, setSelectedConnections] = useState<number[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadConnections();
  }, []);

  const loadConnections = async () => {
    try {
      const data = await connectionsAPI.listConnections();
      setConnections(data.connections);
    } catch (error) {
      console.error('Failed to load connections:', error);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || selectedConnections.length === 0) return;

    setLoading(true);
    try {
      const session = await chatAPI.createSession({
        name: name.trim(),
        connection_ids: selectedConnections,
      });
      onCreated(session);
    } catch (error) {
      console.error('Failed to create session:', error);
      alert('Failed to create chat session');
    } finally {
      setLoading(false);
    }
  };

  const toggleConnection = (id: number) => {
    setSelectedConnections((prev) =>
      prev.includes(id) ? prev.filter((cid) => cid !== id) : [...prev, id]
    );
  };

  return (
    <div className="fixed inset-0 bg-black/40 backdrop-blur-xl flex items-center justify-center z-[100] animate-fadeIn p-4">
      <div className="glass-card max-w-md w-full shadow-2xl animate-scaleUp border-white/10">
        <div className="flex items-center justify-between p-6 border-b border-white/5">
          <h3 className="text-lg font-black uppercase tracking-tight text-gray-900 dark:text-white">New Session</h3>
          <button
            onClick={onClose}
            className="p-2 glass-panel rounded-xl text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition-colors"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          <div>
            <label className="block text-[10px] font-black uppercase tracking-widest text-gray-500 dark:text-gray-400 mb-2 ml-1">
              Session Name
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g., Production Analysis"
              className="w-full px-4 py-3 glass-panel bg-white/5 dark:bg-black/20 border-white/10 rounded-xl text-gray-900 dark:text-white placeholder-gray-400 focus:ring-2 focus:ring-blue-500/50 outline-none transition-all font-medium"
              required
            />
          </div>

          <div>
            <label className="block text-[10px] font-black uppercase tracking-widest text-gray-500 dark:text-gray-400 mb-2 ml-1">
              Connect Databases ({selectedConnections.length})
            </label>
            <div className="glass-panel bg-white/5 dark:bg-black/20 border-white/10 rounded-xl max-h-48 overflow-y-auto custom-scrollbar p-2 space-y-1">
              {connections.length === 0 ? (
                <p className="p-4 text-xs text-gray-500 dark:text-gray-400 text-center font-bold">
                  No connections found.
                </p>
              ) : (
                connections.map((conn) => (
                  <label
                    key={conn.id}
                    className={`flex items-center p-3 rounded-lg cursor-pointer transition-all ${selectedConnections.includes(conn.id)
                      ? 'bg-blue-600/10 border border-blue-500/30'
                      : 'hover:bg-white/5 border border-transparent'
                      }`}
                  >
                    <input
                      type="checkbox"
                      checked={selectedConnections.includes(conn.id)}
                      onChange={() => toggleConnection(conn.id)}
                      className="hidden"
                    />
                    <div className={`w-4 h-4 rounded border flex items-center justify-center mr-3 transition-all ${selectedConnections.includes(conn.id) ? 'bg-blue-600 border-blue-600' : 'border-white/20'}`}>
                      {selectedConnections.includes(conn.id) && (
                        <svg className="w-2.5 h-2.5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                        </svg>
                      )}
                    </div>
                    <div className="flex-1">
                      <p className="text-xs font-black uppercase tracking-wider text-gray-900 dark:text-white">{conn.name}</p>
                      <p className="text-[10px] text-gray-500 font-bold uppercase opacity-60">
                        {conn.database_type} • {conn.database_name}
                      </p>
                    </div>
                  </label>
                ))
              )}
            </div>
          </div>

          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-6 py-3 text-[10px] font-black uppercase tracking-widest text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading || !name.trim() || selectedConnections.length === 0}
              className="px-6 py-3 text-[10px] font-black uppercase tracking-widest bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-xl hover:scale-105 active:scale-95 transition-all shadow-xl shadow-blue-500/20 disabled:opacity-30 disabled:hover:scale-100"
            >
              {loading ? 'Creating...' : 'Launch Session'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
