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
  const [loading, setLoading] = useState(false);

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
    <div className="p-4 border-b border-gray-200">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-gray-700">Chat Sessions</h3>
        <button
          onClick={() => setShowCreateModal(true)}
          className="px-3 py-1 text-xs bg-primary-600 text-white rounded hover:bg-primary-700"
        >
          + New
        </button>
      </div>

      <div className="space-y-2">
        {/* Default session (no chat context) */}
        <button
          onClick={() => onSessionChange(null)}
          className={`w-full text-left px-3 py-2 rounded text-sm transition-colors ${
            !currentSession
              ? 'bg-primary-100 text-primary-700 font-medium'
              : 'hover:bg-gray-100 text-gray-700'
          }`}
        >
          <div className="flex items-center">
            <span className="text-lg mr-2">💬</span>
            <span>Default Query</span>
          </div>
          <p className="text-xs text-gray-500 mt-1">Single database mode</p>
        </button>

        {/* Chat sessions */}
        {sessions.map((session) => (
          <div
            key={session.id}
            className={`relative group rounded ${
              currentSession?.id === session.id
                ? 'bg-primary-100 ring-2 ring-primary-500'
                : 'hover:bg-gray-100'
            }`}
          >
            <button
              onClick={() => onSessionChange(session)}
              className="w-full text-left px-3 py-2 text-sm"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center flex-1">
                  <span className="text-lg mr-2">💬</span>
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-gray-900 truncate">{session.name}</p>
                    <p className="text-xs text-gray-500 mt-1">
                      {session.connections.length} database{session.connections.length !== 1 ? 's' : ''} • {session.message_count} messages
                    </p>
                  </div>
                </div>
                <button
                  onClick={(e) => handleDeleteSession(session.id, e)}
                  className="opacity-0 group-hover:opacity-100 ml-2 p-1 text-red-600 hover:bg-red-100 rounded"
                  title="Delete session"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                </button>
              </div>
              {session.connections.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1">
                  {session.connections.map((conn) => (
                    <span
                      key={conn.id}
                      className="inline-flex items-center px-2 py-0.5 rounded text-xs bg-blue-100 text-blue-700"
                    >
                      {conn.name}
                    </span>
                  ))}
                </div>
              )}
            </button>
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
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
        <div className="flex items-center justify-between p-4 border-b">
          <h3 className="text-lg font-semibold">New Chat Session</h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-4">
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Session Name
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g., Production Analysis"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-primary-500 focus:border-primary-500"
              required
            />
          </div>

          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Select Databases ({selectedConnections.length} selected)
            </label>
            <div className="border border-gray-300 rounded-md max-h-48 overflow-y-auto">
              {connections.length === 0 ? (
                <p className="p-4 text-sm text-gray-500 text-center">
                  No database connections found. Please add a connection first.
                </p>
              ) : (
                connections.map((conn) => (
                  <label
                    key={conn.id}
                    className="flex items-center p-3 hover:bg-gray-50 cursor-pointer border-b last:border-b-0"
                  >
                    <input
                      type="checkbox"
                      checked={selectedConnections.includes(conn.id)}
                      onChange={() => toggleConnection(conn.id)}
                      className="mr-3 h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                    />
                    <div className="flex-1">
                      <p className="text-sm font-medium text-gray-900">{conn.name}</p>
                      <p className="text-xs text-gray-500">
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
              className="px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 rounded-md"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading || !name.trim() || selectedConnections.length === 0}
              className="px-4 py-2 text-sm bg-primary-600 text-white rounded-md hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Creating...' : 'Create Session'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
