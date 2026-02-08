import { useState, useEffect } from 'react';
import { FileSpreadsheet, RefreshCw, Loader2, AlertCircle, Table, Columns, Hash, X } from 'lucide-react';
import { filesAPI } from '../services/api';
import type { FileSource, FileSchemaResponse, FilePreviewResponse } from '../types/api';

interface Props {
  fileId: number;
  onClose?: () => void;
}

export default function FilePreviewPanel({ fileId, onClose }: Props) {
  const [file, setFile] = useState<FileSource | null>(null);
  const [schema, setSchema] = useState<FileSchemaResponse | null>(null);
  const [preview, setPreview] = useState<FilePreviewResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'schema' | 'preview'>('schema');

  useEffect(() => {
    loadFileData();
  }, [fileId]);

  const loadFileData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [fileData, schemaData, previewData] = await Promise.all([
        filesAPI.getFile(fileId),
        filesAPI.getFileSchema(fileId),
        filesAPI.getFilePreview(fileId, 20),
      ]);
      setFile(fileData);
      setSchema(schemaData);
      setPreview(previewData);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load file data');
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    setError(null);
    try {
      await filesAPI.refreshFileSchema(fileId);
      await loadFileData();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to refresh schema');
    } finally {
      setRefreshing(false);
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const getTypeColor = (type: string) => {
    const t = type.toUpperCase();
    if (t.includes('INT') || t.includes('NUMBER') || t.includes('BIGINT')) return 'text-blue-500';
    if (t.includes('FLOAT') || t.includes('DOUBLE') || t.includes('DECIMAL')) return 'text-purple-500';
    if (t.includes('VARCHAR') || t.includes('TEXT') || t.includes('STRING')) return 'text-green-500';
    if (t.includes('DATE') || t.includes('TIME') || t.includes('TIMESTAMP')) return 'text-orange-500';
    if (t.includes('BOOL')) return 'text-pink-500';
    return 'text-gray-500';
  };

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="text-center">
          <Loader2 className="w-8 h-8 text-green-500 animate-spin mx-auto mb-3" />
          <p className="text-sm text-gray-500">Loading file data...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="text-center">
          <AlertCircle className="w-8 h-8 text-red-500 mx-auto mb-3" />
          <p className="text-sm text-red-500 mb-4">{error}</p>
          <button
            onClick={loadFileData}
            className="px-4 py-2 bg-gray-100 dark:bg-gray-800 rounded-lg text-sm hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  if (!file || !schema || !preview) {
    return null;
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-white/5 bg-white/5">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-green-500/10 text-green-500">
            <FileSpreadsheet className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-gray-900 dark:text-white">{file.name}</h3>
            <p className="text-xs text-gray-500">
              {file.file_type.toUpperCase()} • {formatFileSize(file.file_size_bytes)} • {schema.row_count.toLocaleString()} rows
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="p-2 glass-panel rounded-lg hover:bg-white/10 transition-colors disabled:opacity-50"
            title="Refresh Schema"
          >
            <RefreshCw className={`w-4 h-4 text-gray-500 ${refreshing ? 'animate-spin' : ''}`} />
          </button>
          {onClose && (
            <button
              onClick={onClose}
              className="p-2 glass-panel rounded-lg hover:bg-white/10 transition-colors"
              title="Close"
            >
              <X className="w-4 h-4 text-gray-500" />
            </button>
          )}
        </div>
      </div>

      {/* Tab Switcher */}
      <div className="flex border-b border-white/5">
        <button
          onClick={() => setActiveTab('schema')}
          className={`flex-1 px-4 py-2.5 text-xs font-bold uppercase tracking-wider transition-all flex items-center justify-center gap-2 ${
            activeTab === 'schema'
              ? 'text-green-500 border-b-2 border-green-500 bg-green-500/5'
              : 'text-gray-500 hover:text-gray-300'
          }`}
        >
          <Columns className="w-3.5 h-3.5" />
          Schema ({schema.columns.length})
        </button>
        <button
          onClick={() => setActiveTab('preview')}
          className={`flex-1 px-4 py-2.5 text-xs font-bold uppercase tracking-wider transition-all flex items-center justify-center gap-2 ${
            activeTab === 'preview'
              ? 'text-green-500 border-b-2 border-green-500 bg-green-500/5'
              : 'text-gray-500 hover:text-gray-300'
          }`}
        >
          <Table className="w-3.5 h-3.5" />
          Preview ({preview.row_count})
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto">
        {/* Schema Tab */}
        {activeTab === 'schema' && (
          <div className="p-4 space-y-2">
            {schema.columns.map((col, idx) => (
              <div
                key={col.name}
                className="glass-panel p-3 rounded-xl flex items-center justify-between gap-4"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <span className="text-[10px] font-bold text-gray-400 w-6 text-right">
                    {idx + 1}
                  </span>
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                      {col.name}
                    </p>
                    {schema.sample_values[col.name] && schema.sample_values[col.name].length > 0 && (
                      <p className="text-[11px] text-gray-500 truncate">
                        e.g. {schema.sample_values[col.name].slice(0, 3).join(', ')}
                      </p>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                  <span className={`text-[11px] font-mono font-bold ${getTypeColor(col.type)}`}>
                    {col.type}
                  </span>
                  {col.nullable && (
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-800 text-gray-500">
                      NULL
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Preview Tab */}
        {activeTab === 'preview' && (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-white/5 sticky top-0">
                <tr>
                  <th className="px-3 py-2 text-left text-[10px] font-bold uppercase tracking-wider text-gray-500 w-10">
                    #
                  </th>
                  {preview.columns.map((col) => (
                    <th
                      key={col}
                      className="px-3 py-2 text-left text-[10px] font-bold uppercase tracking-wider text-gray-500 whitespace-nowrap"
                    >
                      {col}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {preview.data.map((row, rowIdx) => (
                  <tr key={rowIdx} className="hover:bg-white/5 transition-colors">
                    <td className="px-3 py-2 text-[10px] text-gray-400 font-mono">
                      {rowIdx + 1}
                    </td>
                    {preview.columns.map((col) => (
                      <td
                        key={col}
                        className="px-3 py-2 text-gray-700 dark:text-gray-300 whitespace-nowrap max-w-[200px] truncate"
                        title={String(row[col] ?? '')}
                      >
                        {row[col] === null ? (
                          <span className="text-gray-400 italic">null</span>
                        ) : (
                          String(row[col])
                        )}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
            {preview.truncated && (
              <div className="p-3 text-center text-xs text-gray-500 bg-white/5 border-t border-white/5">
                Showing {preview.row_count} of {preview.total_rows.toLocaleString()} rows
              </div>
            )}
          </div>
        )}
      </div>

      {/* Footer with Table Name */}
      <div className="p-3 border-t border-white/5 bg-white/5">
        <div className="flex items-center gap-2 text-xs">
          <Hash className="w-3.5 h-3.5 text-gray-400" />
          <span className="text-gray-500">Query as:</span>
          <code className="font-mono text-green-500 bg-green-500/10 px-2 py-0.5 rounded">
            {file.duckdb_table_name}
          </code>
        </div>
      </div>
    </div>
  );
}
