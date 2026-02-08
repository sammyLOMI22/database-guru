import { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { Database, FileSpreadsheet, Plus, Trash2, Check, Circle, Pencil, Loader2, Upload, Eye } from 'lucide-react';
import DatabaseConnectionModal from './DatabaseConnectionModal';
import FileUploadModal from './FileUploadModal';
import FilePreviewPanel from './FilePreviewPanel';
import type { FileSource } from '../types/api';
import { connectionsAPI, filesAPI } from '../services/api';

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
  onConnectionSelect?: (connectionId: number) => void;
  onFileSelect?: (fileId: number) => void;
  onFileDeleted?: () => void;
  selectedConnectionIds?: number[];
  selectedFileIds?: number[];
  sessionId?: string;
  onDataSourcesChange?: (connections: number[], files: number[]) => void;
}

type SourceType = 'databases' | 'files';

export default function DataSourcesPanel({
  onConnectionSelect,
  onFileSelect,
  onFileDeleted,
  selectedConnectionIds = [],
  sessionId,
  onDataSourcesChange,
}: Props) {
  const [activeTab, setActiveTab] = useState<SourceType>('databases');
  const [connections, setConnections] = useState<DatabaseConnection[]>([]);
  const [fileSources, setFileSources] = useState<FileSource[]>([]);
  const [isDbModalOpen, setIsDbModalOpen] = useState(false);
  const [isFileModalOpen, setIsFileModalOpen] = useState(false);
  const [previewFileId, setPreviewFileId] = useState<number | null>(null);
  const [editingConnection, setEditingConnection] = useState<DatabaseConnection | undefined>();
  const [loading, setLoading] = useState(false);
  const [sessionFileIds, setSessionFileIds] = useState<number[]>([]);

  // Load data on mount
  useEffect(() => {
    loadConnections();
    loadFileSources();
    loadSessionFiles();
  }, [sessionId]);

  const loadConnections = async () => {
    try {
      const data = await connectionsAPI.listConnections();
      setConnections(data.connections || []);
    } catch (error) {
      console.error('Failed to load connections:', error);
    }
  };

  const loadFileSources = async () => {
    try {
      const response = await filesAPI.listFiles(sessionId);
      setFileSources(response.files || []);
    } catch (error) {
      console.error('Failed to load file sources:', error);
    }
  };

  const loadSessionFiles = async () => {
    if (!sessionId) {
      setSessionFileIds([]);
      return;
    }
    try {
      const response = await filesAPI.getSessionFiles(sessionId);
      setSessionFileIds(response.active_file_source_ids || []);
    } catch (error) {
      console.error('Failed to load session files:', error);
    }
  };

  const handleAddConnection = () => {
    setEditingConnection(undefined);
    setIsDbModalOpen(true);
  };

  const handleEditConnection = (connection: DatabaseConnection) => {
    setEditingConnection(connection);
    setIsDbModalOpen(true);
  };

  const handleSaveConnection = async (connectionData: any) => {
    setLoading(true);
    try {
      if (editingConnection) {
        await connectionsAPI.updateConnection(editingConnection.id, connectionData);
      } else {
        await connectionsAPI.createConnection(connectionData);
      }
      await loadConnections();
      setIsDbModalOpen(false);
    } catch (error: any) {
      const detail = error.response?.data?.detail || error.message;
      alert(`Failed to save connection: ${detail}`);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteConnection = async (id: number) => {
    if (!confirm('Are you sure you want to delete this connection?')) return;

    try {
      await connectionsAPI.deleteConnection(id);
      await loadConnections();
    } catch (error) {
      console.error('Failed to delete connection:', error);
    }
  };

  const handleSelectConnection = async (id: number) => {
    try {
      await connectionsAPI.activateConnection(id);
      await loadConnections();
      onConnectionSelect?.(id);
    } catch (error) {
      console.error('Failed to activate connection:', error);
    }
  };

  const handleFileUploadSuccess = async (fileSource: FileSource) => {
    await loadFileSources();
    setIsFileModalOpen(false);
    onFileSelect?.(fileSource.id);
    // Refresh session file list so the new file shows the "in session" checkmark
    await loadSessionFiles();
  };

  const handleDeleteFile = async (id: number) => {
    if (!confirm('Are you sure you want to delete this file?')) return;

    try {
      await filesAPI.deleteFile(id);
      await loadFileSources();
      await loadSessionFiles();
      onFileDeleted?.();
    } catch (error) {
      console.error('Failed to delete file:', error);
    }
  };

  const handleSelectFile = async (id: number) => {
    if (!sessionId) return;
    try {
      const isActive = sessionFileIds.includes(id);
      if (isActive) {
        await filesAPI.removeFileFromSession(sessionId, id);
        setSessionFileIds(prev => prev.filter(fid => fid !== id));
        onFileDeleted?.();
      } else {
        await filesAPI.addFileToSession(sessionId, id);
        setSessionFileIds(prev => [...prev, id]);
        onFileSelect?.(id);
      }
    } catch (error) {
      console.error('Failed to toggle file in session:', error);
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const getFileTypeColor = (type: string) => {
    switch (type) {
      case 'csv': return 'text-green-500 bg-green-500/10';
      case 'xlsx': return 'text-blue-500 bg-blue-500/10';
      case 'xls': return 'text-orange-500 bg-orange-500/10';
      default: return 'text-gray-500 bg-gray-500/10';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'ready': return 'text-green-500';
      case 'processing': return 'text-yellow-500';
      case 'error': return 'text-red-500';
      case 'deleted': return 'text-gray-400';
      default: return 'text-gray-500';
    }
  };

  const totalSources = connections.length + fileSources.length;

  return (
    <div className="flex flex-col h-full relative">
      {/* Header */}
      <div className="flex items-center justify-between p-5 border-b border-white/5 bg-white/5 dark:bg-black/20">
        <h3 className="text-[11px] font-black uppercase tracking-[0.2em] text-gray-900 dark:text-white flex items-center gap-2.5">
          <div className="p-1 px-1.5 glass-panel rounded-lg text-blue-500 shadow-lg shadow-blue-500/10">
            <Database className="w-4 h-4" />
          </div>
          Data Sources
          <span className="text-[10px] font-medium text-gray-500">({totalSources})</span>
        </h3>
        <div className="flex gap-1">
          <button
            onClick={handleAddConnection}
            className="p-2 glass-panel rounded-xl text-blue-500 hover:text-blue-600 hover:scale-110 active:scale-95 transition-all shadow-lg shadow-blue-500/5 group"
            title="Add Database"
          >
            <Plus className="w-4 h-4 group-hover:rotate-90 transition-transform duration-300" />
          </button>
          <button
            onClick={() => setIsFileModalOpen(true)}
            className="p-2 glass-panel rounded-xl text-green-500 hover:text-green-600 hover:scale-110 active:scale-95 transition-all shadow-lg shadow-green-500/5 group"
            title="Upload File"
          >
            <Upload className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Tab Switcher */}
      <div className="flex border-b border-white/5">
        <button
          onClick={() => setActiveTab('databases')}
          className={`flex-1 px-4 py-2.5 text-xs font-bold uppercase tracking-wider transition-all flex items-center justify-center gap-2 ${
            activeTab === 'databases'
              ? 'text-blue-500 border-b-2 border-blue-500 bg-blue-500/5'
              : 'text-gray-500 hover:text-gray-300'
          }`}
        >
          <Database className="w-3.5 h-3.5" />
          Databases ({connections.length})
        </button>
        <button
          onClick={() => setActiveTab('files')}
          className={`flex-1 px-4 py-2.5 text-xs font-bold uppercase tracking-wider transition-all flex items-center justify-center gap-2 ${
            activeTab === 'files'
              ? 'text-green-500 border-b-2 border-green-500 bg-green-500/5'
              : 'text-gray-500 hover:text-gray-300'
          }`}
        >
          <FileSpreadsheet className="w-3.5 h-3.5" />
          Files ({fileSources.length})
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto">
        {/* Databases Tab */}
        {activeTab === 'databases' && (
          <>
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
                  const isSelected = selectedConnectionIds.includes(conn.id);
                  return (
                    <div
                      key={conn.id}
                      onClick={() => handleSelectConnection(conn.id)}
                      className={`group p-4 rounded-2xl border transition-all duration-300 cursor-pointer relative overflow-hidden ${
                        conn.is_active
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
                            <div className={`p-1.5 rounded-lg transition-all ${
                              conn.is_active
                                ? 'bg-blue-500 text-white shadow-lg shadow-blue-500/30 scale-110'
                                : 'bg-black/5 dark:bg-white/5 text-gray-400'
                            }`}>
                              {conn.is_active ? <Check className="w-3.5 h-3.5" /> : <Circle className="w-3.5 h-3.5" />}
                            </div>
                            <span className="text-sm font-black uppercase tracking-tight text-gray-900 dark:text-white truncate">
                              {conn.name}
                            </span>
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
          </>
        )}

        {/* Files Tab */}
        {activeTab === 'files' && (
          <>
            {fileSources.length === 0 ? (
              <div className="p-8 text-center mt-10">
                <FileSpreadsheet className="w-12 h-12 text-gray-300 dark:text-gray-700 mx-auto mb-3" />
                <p className="text-gray-500 dark:text-gray-400 text-sm mb-4">No files uploaded yet</p>
                <button
                  onClick={() => setIsFileModalOpen(true)}
                  className="px-4 py-2 bg-green-500 dark:bg-green-600 text-white text-sm rounded-lg hover:bg-green-600 dark:hover:bg-green-500 transition-colors shadow-sm flex items-center gap-2 mx-auto"
                >
                  <Upload className="w-4 h-4" />
                  Upload Your First File
                </button>
              </div>
            ) : (
              <div className="p-2 space-y-1">
                {!sessionId && fileSources.length > 0 && (
                  <div className="px-3 py-2 mb-2 text-[11px] text-gray-500 dark:text-gray-400 bg-yellow-500/5 border border-yellow-500/20 rounded-xl text-center">
                    Select a chat session to add files to it
                  </div>
                )}
                {fileSources.map((file) => {
                  const isInSession = sessionFileIds.includes(file.id);
                  const isDeleted = file.processing_status === 'deleted';
                  const isReady = file.processing_status === 'ready';
                  const canToggle = isReady && !!sessionId;
                  return (
                    <div
                      key={file.id}
                      onClick={() => canToggle && handleSelectFile(file.id)}
                      className={`group p-4 rounded-2xl border transition-all duration-300 relative overflow-hidden ${
                        isDeleted ? 'cursor-default opacity-60'
                        : !isReady ? 'cursor-not-allowed opacity-60'
                        : !sessionId ? 'cursor-default'
                        : 'cursor-pointer'
                      } ${
                        isInSession && isReady
                          ? 'glass-card bg-green-500/5 border-green-500/30 shadow-[0_10px_30px_rgba(34,197,94,0.1)]'
                          : 'glass-panel bg-transparent border-transparent hover:bg-white/5 hover:border-white/10'
                      }`}
                    >
                      {isInSession && isReady && (
                        <div className="absolute top-0 right-0 w-24 h-24 bg-green-500/10 blur-3xl -mr-12 -mt-12 pointer-events-none" />
                      )}
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-3 mb-2">
                            <div className={`p-1.5 rounded-lg transition-all ${
                              isDeleted
                                ? 'bg-gray-500/20 text-gray-400'
                                : isInSession
                                ? 'bg-green-500 text-white shadow-lg shadow-green-500/30 scale-110'
                                : getFileTypeColor(file.file_type)
                            }`}>
                              {isInSession && !isDeleted ? <Check className="w-3.5 h-3.5" /> : <FileSpreadsheet className="w-3.5 h-3.5" />}
                            </div>
                            <span className={`text-sm font-black uppercase tracking-tight truncate ${isDeleted ? 'text-gray-400 dark:text-gray-500' : 'text-gray-900 dark:text-white'}`}>
                              {file.name}
                            </span>
                          </div>
                          <div className="pl-1 space-y-2">
                            <div className="flex items-center gap-2 flex-wrap">
                              <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-[11px] font-black uppercase tracking-widest ${getFileTypeColor(file.file_type)}`}>
                                {file.file_type.toUpperCase()}
                              </span>
                              {!isDeleted && (
                                <>
                                  <span className="text-[11px] text-gray-400 dark:text-gray-500 font-bold">
                                    {formatFileSize(file.file_size_bytes)}
                                  </span>
                                  {file.row_count && (
                                    <span className="text-[11px] text-gray-400 dark:text-gray-500 font-bold">
                                      {file.row_count.toLocaleString()} rows
                                    </span>
                                  )}
                                </>
                              )}
                            </div>
                            <div className="flex items-center gap-2">
                              {isDeleted ? (
                                <span className="text-[11px] font-bold italic text-gray-400 tracking-widest">
                                  File removed
                                </span>
                              ) : (
                                <>
                                  <span className={`text-[11px] font-bold uppercase tracking-widest ${getStatusColor(file.processing_status)}`}>
                                    {file.processing_status === 'processing' && (
                                      <Loader2 className="w-3 h-3 inline animate-spin mr-1" />
                                    )}
                                    {file.processing_status}
                                  </span>
                                  {file.sheet_name && (
                                    <span className="text-[11px] text-gray-500 font-medium">
                                      Sheet: {file.sheet_name}
                                    </span>
                                  )}
                                </>
                              )}
                            </div>
                          </div>
                        </div>
                        {!isDeleted && (
                          <div className="flex items-center gap-1">
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                setPreviewFileId(file.id);
                              }}
                              className="opacity-0 group-hover:opacity-100 p-1 hover:bg-blue-50 dark:hover:bg-blue-900/30 rounded transition-all"
                              title="Preview"
                            >
                              <Eye className="w-3.5 h-3.5 text-blue-600 dark:text-blue-400" />
                            </button>
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                handleDeleteFile(file.id);
                              }}
                              className="opacity-0 group-hover:opacity-100 p-1 hover:bg-red-50 dark:hover:bg-red-900/30 rounded transition-all"
                              title="Delete"
                            >
                              <Trash2 className="w-3.5 h-3.5 text-red-600 dark:text-red-400" />
                            </button>
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </>
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
        isOpen={isDbModalOpen}
        onClose={() => !loading && setIsDbModalOpen(false)}
        onSave={handleSaveConnection}
        connection={editingConnection}
      />

      <FileUploadModal
        isOpen={isFileModalOpen}
        onClose={() => setIsFileModalOpen(false)}
        onSuccess={handleFileUploadSuccess}
        sessionId={sessionId}
      />

      {/* File Preview Modal - portal to escape sidebar containment */}
      {previewFileId !== null && createPortal(
        <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/60 backdrop-blur-sm" onClick={() => setPreviewFileId(null)}>
          <div
            className="bg-gray-900 border border-white/10 w-[90vw] max-w-5xl rounded-2xl shadow-2xl overflow-hidden flex flex-col"
            style={{ maxHeight: '85vh' }}
            onClick={(e) => e.stopPropagation()}
          >
            <FilePreviewPanel
              fileId={previewFileId}
              onClose={() => setPreviewFileId(null)}
            />
          </div>
        </div>,
        document.body,
      )}
    </div>
  );
}
