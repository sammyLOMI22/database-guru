import { useState, useEffect } from 'react';
import { chatAPI, connectionsAPI } from '../services/api';
import type { ChatSession, DatabaseConnection } from '../types/api';

interface ChatSessionSelectorProps {
  currentSession: ChatSession | null;
  onSessionChange: (session: ChatSession | null) => void;
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
    <div className="p-4 border-b border-gray-200 dark:border-gray-700 transition-colors">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">Chat Sessions</h3>
        <button
          onClick={() => setShowCreateModal(true)}
          className="px-3 py-1 text-xs bg-primary-600 dark:bg-primary-700 text-white rounded hover:bg-primary-700 dark:hover:bg-primary-600 transition-colors"
        >
          + New
        </button>
      </div>

      <div className="space-y-2">
        {/* Default session (no chat context) */}
        <button
          onClick={() => onSessionChange(null)}
          className={`w-full text-left px-3 py-2 rounded text-sm transition-colors ${!currentSession
              ? 'bg-primary-100 dark:bg-primary-900/40 text-primary-700 dark:text-primary-300 font-medium'
              : 'hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-400'
            }`}
        >
          <div className="flex items-center">
            <span className="text-lg mr-2">💬</span>
            <span>Default Query</span>
          </div>
          <p className="text-xs text-gray-500 dark:text-gray-500 mt-1">Single database mode</p>
        </button>

        {/* Chat sessions */}
        {sessions.map((session) => (
          <div
            key={session.id}
            className={`relative group rounded transition-all duration-200 ${currentSession?.id === session.id
                ? 'bg-primary-100 dark:bg-primary-900/30 ring-2 ring-primary-500 dark:ring-primary-700'
                : 'hover:bg-gray-100 dark:hover:bg-gray-700'
              }`}
          >
            <div className="flex items-stretch">
              <button
                onClick={() => onSessionChange(session)}
                className="flex-1 text-left px-3 py-2 text-sm"
              >
                <div className="flex items-center">
                  <span className="text-lg mr-2">💬</span>
                  <div className="flex-1 min-w-0">
                    <p className={`font-medium truncate ${currentSession?.id === session.id ? 'text-gray-900 dark:text-white' : 'text-gray-700 dark:text-gray-300'}`}>{session.name}</p>
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                      {session.connections.length} database{session.connections.length !== 1 ? 's' : ''} • {session.message_count} messages
                    </p>
                  </div>
                </div>
                {session.connections.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1">
                    {session.connections.map((conn) => (
                      <span
                        key={conn.id}
                        className="inline-flex items-center px-2 py-0.5 rounded text-xs bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300 transition-colors"
                      >
                        {conn.name}
                      </span>
                    ))}
                  </div>
                )}
              </button>
              <button
                onClick={(e) => handleDeleteSession(session.id, e)}
                className="opacity-0 group-hover:opacity-100 px-3 py-2 text-red-600 dark:text-red-400 hover:bg-red-100 dark:hover:bg-red-900/30 rounded transition-all"
                title="Delete session"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
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
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 backdrop-blur-sm">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-md w-full mx-4 overflow-hidden transition-colors">
        <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">New Chat Session</h3>
          <button
            onClick={onClose}
            className="text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-4">
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Session Name
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g., Production Analysis"
              className="w-full px-3 py-2 bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-700 rounded-md text-gray-900 dark:text-white focus:ring-primary-500 focus:border-primary-500 transition-colors"
              required
            />
          </div>

          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Select Databases ({selectedConnections.length} selected)
            </label>
            <div className="border border-gray-300 dark:border-gray-700 rounded-md max-h-48 overflow-y-auto">
              {connections.length === 0 ? (
                <p className="p-4 text-sm text-gray-500 dark:text-gray-400 text-center">
                  No database connections found. Please add a connection first.
                </p>
              ) : (
                connections.map((conn) => (
                  <label
                    key={conn.id}
                    className="flex items-center p-3 hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer border-b border-gray-100 dark:border-gray-700 last:border-b-0 transition-colors"
                  >
                    <input
                      type="checkbox"
                      checked={selectedConnections.includes(conn.id)}
                      onChange={() => toggleConnection(conn.id)}
                      className="mr-3 h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 rounded"
                    />
                    <div className="flex-1">
                      <p className="text-sm font-medium text-gray-900 dark:text-white">{conn.name}</p>
                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        {conn.database_type} • {conn.database_name}
                      </p>
                    </div>
                  </label>
                ))
              )}
            </div>
          </div>

          <div className="flex justify-end space-x-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-md transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading || !name.trim() || selectedConnections.length === 0}
              className="px-4 py-2 text-sm bg-primary-600 dark:bg-primary-700 text-white rounded-md hover:bg-primary-700 dark:hover:bg-primary-600 disabled:opacity-50 disabled:bg-gray-300 dark:disabled:bg-gray-700 disabled:cursor-not-allowed transition-colors"
            >
              {loading ? 'Creating...' : 'Create Session'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
