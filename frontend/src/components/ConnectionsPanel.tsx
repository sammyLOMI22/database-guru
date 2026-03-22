import { useState, useEffect } from 'react';
import { Database, Plus, Trash2, Check, Circle, Pencil, Loader2, Shield } from 'lucide-react';
import DatabaseConnectionModal from './DatabaseConnectionModal';
import WritePermissionsModal from './WritePermissionsModal';

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
  const [permissionsConn, setPermissionsConn] = useState<DatabaseConnection | null>(null);

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
      <div className="flex items-center justify-between p-5 border-b border-white/5 bg-white/5 dark:bg-black/20">
        <h3 className="text-[11px] font-black uppercase tracking-[0.2em] text-gray-900 dark:text-white flex items-center gap-2.5">
          <div className="p-1 px-1.5 glass-panel rounded-lg text-blue-500 shadow-lg shadow-blue-500/10">
            <Database className="w-4 h-4" />
          </div>
          Connections
        </h3>
        <button
          onClick={handleAddConnection}
          className="p-2 glass-panel rounded-xl text-blue-500 hover:text-blue-600 hover:scale-110 active:scale-95 transition-all shadow-lg shadow-blue-500/5 group"
          title="Add Connection"
        >
          <Plus className="w-4 h-4 group-hover:rotate-90 transition-transform duration-300" />
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
                  className={`group p-4 rounded-2xl border transition-all duration-300 cursor-pointer relative overflow-hidden ${conn.is_active
                    ? 'glass-card bg-blue-500/5 border-blue-500/30 shadow-[0_10px_30px_rgba(59,130,246,0.1)]'
                    : isSelected
                      ? 'glass-card bg-white/10 border-white/20'
                      : 'glass-panel bg-transparent border-transparent hover:bg-white/5 hover:border-white/10'
                    }`}
                >
                  {conn.is_active && (
                    <div className="absolute top-0 right-0 w-24 h-24 bg-blue-500/10 blur-3xl -mr-12 -mt-12 pointer-events-none" />
                  )}
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-3 mb-2">
                        <div className={`p-1.5 rounded-lg transition-all ${conn.is_active ? 'bg-blue-500 text-white shadow-lg shadow-blue-500/30 scale-110' : 'bg-black/5 dark:bg-white/5 text-gray-400'}`}>
                          {conn.is_active ? <Check className="w-3.5 h-3.5" /> : <Circle className="w-3.5 h-3.5" />}
                        </div>
                        <span className="text-sm font-black uppercase tracking-tight text-gray-900 dark:text-white truncate">{conn.name}</span>
                      </div>
                      <div className="pl-1 space-y-2">
                        <div className="flex items-center gap-2">
                          <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[11px] font-black uppercase tracking-widest bg-black/10 dark:bg-white/10 text-gray-600 dark:text-gray-400 transition-colors">
                            {conn.database_type.toUpperCase()}
                          </span>
                          {conn.host && (
                            <span className="text-[11px] text-gray-400 dark:text-gray-500 font-bold uppercase tracking-widest">
                              {conn.host}
                            </span>
                          )}
                        </div>
                        <p className="text-[11px] text-gray-500 dark:text-gray-400 font-bold uppercase tracking-widest truncate max-w-[180px]" title={conn.database_name}>
                          DB: {conn.database_name}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-1">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setPermissionsConn(conn);
                        }}
                        className="opacity-0 group-hover:opacity-100 p-1 hover:bg-emerald-50 dark:hover:bg-emerald-900/30 rounded transition-all"
                        title="Write Permissions"
                      >
                        <Shield className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
                      </button>
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

      {/* Modals */}
      <DatabaseConnectionModal
        isOpen={isModalOpen}
        onClose={() => !loading && setIsModalOpen(false)}
        onSave={handleSaveConnection}
        connection={editingConnection}
      />
      {permissionsConn && (
        <WritePermissionsModal
          isOpen={!!permissionsConn}
          onClose={() => setPermissionsConn(null)}
          connectionId={permissionsConn.id}
          connectionName={permissionsConn.name}
        />
      )}
    </div>
  );
}
