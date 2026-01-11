import { useState, useEffect } from 'react';
import { Database, Plus, Trash2, Check, Circle, Pencil, Loader2 } from 'lucide-react';
import DatabaseConnectionModal from './DatabaseConnectionModal';

interface DatabaseConnection {
  id: number;
  name: string;
  database_type: string;
  host?: string;
  port?: number;
  database_name: string;
  is_active: boolean;
}

interface Props {
  onConnectionSelect: (connectionId: number) => void;
  selectedConnectionId?: number;
}

export default function ConnectionsPanel({ onConnectionSelect, selectedConnectionId }: Props) {
  const [connections, setConnections] = useState<DatabaseConnection[]>([]);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingConnection, setEditingConnection] = useState<DatabaseConnection | undefined>();
  const [loading, setLoading] = useState(false);

  // Load connections on mount
  useEffect(() => {
    loadConnections();
  }, []);

  const loadConnections = async () => {
    try {
      const response = await fetch('/api/connections/');
      if (response.ok) {
        const data = await response.json();
        setConnections(data.connections || []);
      }
    } catch (error) {
      console.error('Failed to load connections:', error);
    }
  };

  const handleAddConnection = () => {
    setEditingConnection(undefined);
    setIsModalOpen(true);
  };

  const handleEditConnection = (connection: DatabaseConnection) => {
    setEditingConnection(connection);
    setIsModalOpen(true);
  };

  const handleSaveConnection = async (connectionData: any) => {
    setLoading(true);
    try {
      const url = editingConnection
        ? `/api/connections/${editingConnection.id}`
        : '/api/connections/';
      const method = editingConnection ? 'PUT' : 'POST';

      const response = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(connectionData),
      });

      if (response.ok) {
        await loadConnections();
        setIsModalOpen(false);
      } else {
        const error = await response.json();
        alert(`Failed to save connection: ${error.detail}`);
      }
    } catch (error: any) {
      alert(`Error: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteConnection = async (id: number) => {
    if (!confirm('Are you sure you want to delete this connection?')) return;

    try {
      const response = await fetch(`/api/connections/${id}`, { method: 'DELETE' });
      if (response.ok) {
        await loadConnections();
      }
    } catch (error) {
      console.error('Failed to delete connection:', error);
    }
  };

  const handleSelectConnection = async (id: number) => {
    // Set as active connection
    try {
      const response = await fetch(`/api/connections/${id}/activate`, { method: 'POST' });
      if (response.ok) {
        await loadConnections();
        onConnectionSelect(id);
      }
    } catch (error) {
      console.error('Failed to activate connection:', error);
    }
  };

  return (
    <div className="flex flex-col h-full relative">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
        <h3 className="font-semibold text-gray-900 dark:text-white flex items-center gap-2">
          <Database className="w-4 h-4 text-primary-600 dark:text-primary-400" />
          Connections
        </h3>
        <button
          onClick={handleAddConnection}
          className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
          title="Add Connection"
        >
          <Plus className="w-4 h-4 text-primary-600 dark:text-primary-400" />
        </button>
      </div>

      {/* Connections List */}
      <div className="flex-1 overflow-y-auto">
        {connections.length === 0 ? (
          <div className="p-8 text-center mt-10">
            <Database className="w-12 h-12 text-gray-300 dark:text-gray-700 mx-auto mb-3" />
            <p className="text-gray-500 dark:text-gray-400 text-sm mb-4">No database connections yet</p>
            <button
              onClick={handleAddConnection}
              className="px-4 py-2 bg-primary-500 dark:bg-primary-600 text-white text-sm rounded-lg hover:bg-primary-600 dark:hover:bg-primary-500 transition-colors shadow-sm"
            >
              Add Your First Connection
            </button>
          </div>
        ) : (
          <div className="p-2 space-y-1">
            {connections.map((conn) => {
              const isSelected = selectedConnectionId === conn.id;
              return (
                <div
                  key={conn.id}
                  onClick={() => handleSelectConnection(conn.id)}
                  className={`group p-3 rounded-lg border-2 cursor-pointer transition-all ${conn.is_active
                      ? 'border-primary-500 dark:border-primary-600 bg-primary-50 dark:bg-primary-900/20'
                      : isSelected
                        ? 'border-blue-400 dark:border-blue-700 bg-blue-50 dark:bg-blue-900/20'
                        : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-800'
                    }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        {conn.is_active ? (
                          <Check className="w-4 h-4 text-primary-600 dark:text-primary-400 flex-shrink-0" />
                        ) : (
                          <Circle className="w-4 h-4 text-gray-400 dark:text-gray-600 flex-shrink-0" />
                        )}
                        <span className="font-medium text-gray-900 dark:text-white truncate">{conn.name}</span>
                      </div>
                      <div className="ml-6 space-y-1">
                        <p className="text-xs text-gray-600 dark:text-gray-400">
                          <span className="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-300 transition-colors">
                            {conn.database_type.toUpperCase()}
                          </span>
                        </p>
                        {conn.host && (
                          <p className="text-xs text-gray-600 dark:text-gray-400 font-mono">
                            {conn.host}:{conn.port}
                          </p>
                        )}
                        <p className="text-xs text-gray-700 dark:text-gray-300 font-medium truncate" title={conn.database_name}>
                          {conn.database_name}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-1">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleEditConnection(conn);
                        }}
                        className="opacity-0 group-hover:opacity-100 p-1 hover:bg-blue-50 dark:hover:bg-blue-900/30 rounded transition-all"
                        title="Edit"
                      >
                        <Pencil className="w-3.5 h-3.5 text-blue-600 dark:text-blue-400" />
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDeleteConnection(conn.id);
                        }}
                        className="opacity-0 group-hover:opacity-100 p-1 hover:bg-red-50 dark:hover:bg-red-900/30 rounded transition-all"
                        title="Delete"
                      >
                        <Trash2 className="w-3.5 h-3.5 text-red-600 dark:text-red-400" />
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Loading Overlay */}
      {loading && (
        <div className="absolute inset-0 bg-white/50 dark:bg-black/50 backdrop-blur-sm flex items-center justify-center z-10">
          <div className="flex items-center gap-2 text-primary-600 dark:text-primary-400 bg-white dark:bg-gray-800 px-4 py-2 rounded-lg shadow-lg border border-gray-100 dark:border-gray-700">
            <Loader2 className="w-5 h-5 animate-spin" />
            <span className="text-sm font-medium">Saving...</span>
          </div>
        </div>
      )}

      {/* Modal */}
      <DatabaseConnectionModal
        isOpen={isModalOpen}
        onClose={() => !loading && setIsModalOpen(false)}
        onSave={handleSaveConnection}
        connection={editingConnection}
      />
    </div>
  );
}
