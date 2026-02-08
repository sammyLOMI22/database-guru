import { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { X, Upload, FileSpreadsheet, Loader2, AlertCircle, Check, FileText } from 'lucide-react';
import { filesAPI } from '../services/api';
import type { FileSource, ExcelSheetsResponse } from '../types/api';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (fileSource: FileSource) => void;
  sessionId?: string;
}

type UploadState = 'idle' | 'selecting_sheet' | 'uploading' | 'success' | 'error';

export default function FileUploadModal({ isOpen, onClose, onSuccess, sessionId }: Props) {
  const [uploadState, setUploadState] = useState<UploadState>('idle');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [displayName, setDisplayName] = useState('');
  const [sheets, setSheets] = useState<string[]>([]);
  const [selectedSheet, setSelectedSheet] = useState<string>('');
  const [error, setError] = useState<string>('');
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadedFile, setUploadedFile] = useState<FileSource | null>(null);

  const resetState = () => {
    setUploadState('idle');
    setSelectedFile(null);
    setDisplayName('');
    setSheets([]);
    setSelectedSheet('');
    setError('');
    setUploadProgress(0);
    setUploadedFile(null);
  };

  const handleClose = () => {
    if (uploadState !== 'uploading') {
      resetState();
      onClose();
    }
  };

  const isExcelFile = (file: File) => {
    return file.name.endsWith('.xlsx') || file.name.endsWith('.xls');
  };

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    if (acceptedFiles.length === 0) return;

    const file = acceptedFiles[0];
    setSelectedFile(file);
    setDisplayName(file.name.replace(/\.(csv|xlsx|xls)$/i, ''));
    setError('');

    // If Excel file, fetch sheets
    if (isExcelFile(file)) {
      setUploadState('selecting_sheet');
      try {
        const response: ExcelSheetsResponse = await filesAPI.getExcelSheets(file);
        setSheets(response.sheets);
        if (response.sheets.length > 0) {
          setSelectedSheet(response.sheets[0]);
        }
      } catch (err: any) {
        setError(err.response?.data?.detail || 'Failed to read Excel file');
        setUploadState('error');
      }
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'text/csv': ['.csv'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.ms-excel': ['.xls'],
    },
    maxFiles: 1,
    maxSize: 100 * 1024 * 1024, // 100MB
    disabled: uploadState === 'uploading',
  });

  const handleUpload = async () => {
    if (!selectedFile) return;

    setUploadState('uploading');
    setUploadProgress(0);
    setError('');

    // Simulate progress for UX (actual upload doesn't provide progress events easily)
    const progressInterval = setInterval(() => {
      setUploadProgress(prev => Math.min(prev + 10, 90));
    }, 200);

    try {
      const result = await filesAPI.uploadFile(selectedFile, {
        name: displayName || selectedFile.name,
        sheet_name: selectedSheet || undefined,
        session_id: sessionId,
        is_global: !sessionId,
      });

      setUploadProgress(100);
      setUploadedFile(result);
      setUploadState('success');

      // Notify parent after short delay
      setTimeout(() => {
        onSuccess(result);
      }, 1000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Upload failed');
      setUploadState('error');
    } finally {
      clearInterval(progressInterval);
    }
  };

  if (!isOpen) return null;

  const getFileIcon = () => {
    if (!selectedFile) return <Upload className="w-12 h-12" />;
    if (selectedFile.name.endsWith('.csv')) return <FileText className="w-12 h-12" />;
    return <FileSpreadsheet className="w-12 h-12" />;
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="glass-card w-full max-w-lg mx-4 rounded-2xl shadow-2xl border border-white/10 overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-white/5 bg-white/5">
          <h2 className="text-lg font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <FileSpreadsheet className="w-5 h-5 text-green-500" />
            Upload Data File
          </h2>
          <button
            onClick={handleClose}
            disabled={uploadState === 'uploading'}
            className="p-2 hover:bg-white/10 rounded-lg transition-colors disabled:opacity-50"
          >
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6">
          {/* Success State */}
          {uploadState === 'success' && uploadedFile && (
            <div className="text-center py-8">
              <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-green-500/20 flex items-center justify-center">
                <Check className="w-8 h-8 text-green-500" />
              </div>
              <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-2">
                Upload Complete!
              </h3>
              <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
                {uploadedFile.name} is ready to query
              </p>
              <div className="glass-panel p-4 rounded-xl text-left">
                <div className="text-xs text-gray-500 dark:text-gray-400 space-y-1">
                  <p><span className="font-medium">Table:</span> {uploadedFile.duckdb_table_name}</p>
                  <p><span className="font-medium">Rows:</span> {uploadedFile.row_count?.toLocaleString() || 'Processing...'}</p>
                  <p><span className="font-medium">Type:</span> {uploadedFile.file_type.toUpperCase()}</p>
                </div>
              </div>
            </div>
          )}

          {/* Error State */}
          {uploadState === 'error' && (
            <div className="text-center py-4">
              <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-red-500/20 flex items-center justify-center">
                <AlertCircle className="w-8 h-8 text-red-500" />
              </div>
              <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-2">
                Upload Failed
              </h3>
              <p className="text-sm text-red-500 mb-4">{error}</p>
              <button
                onClick={resetState}
                className="px-4 py-2 bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
              >
                Try Again
              </button>
            </div>
          )}

          {/* Dropzone */}
          {(uploadState === 'idle' || uploadState === 'selecting_sheet') && (
            <>
              <div
                {...getRootProps()}
                className={`border-2 border-dashed rounded-xl p-8 text-center transition-all cursor-pointer ${
                  isDragActive
                    ? 'border-green-500 bg-green-500/10'
                    : selectedFile
                    ? 'border-green-500/50 bg-green-500/5'
                    : 'border-gray-300 dark:border-gray-700 hover:border-green-500/50 hover:bg-green-500/5'
                }`}
              >
                <input {...getInputProps()} />
                <div className={`mx-auto mb-4 ${selectedFile ? 'text-green-500' : 'text-gray-400'}`}>
                  {getFileIcon()}
                </div>
                {selectedFile ? (
                  <div>
                    <p className="text-sm font-medium text-gray-900 dark:text-white mb-1">
                      {selectedFile.name}
                    </p>
                    <p className="text-xs text-gray-500">
                      {formatFileSize(selectedFile.size)}
                    </p>
                  </div>
                ) : (
                  <div>
                    <p className="text-sm text-gray-600 dark:text-gray-300 mb-1">
                      {isDragActive ? 'Drop the file here' : 'Drag & drop a file here'}
                    </p>
                    <p className="text-xs text-gray-400">
                      or click to select (CSV, XLSX, XLS - max 100MB)
                    </p>
                  </div>
                )}
              </div>

              {/* File Options */}
              {selectedFile && (
                <div className="mt-4 space-y-4">
                  {/* Display Name */}
                  <div>
                    <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                      Display Name
                    </label>
                    <input
                      type="text"
                      value={displayName}
                      onChange={(e) => setDisplayName(e.target.value)}
                      placeholder="Enter a name for this file"
                      className="w-full px-3 py-2 glass-panel rounded-lg text-sm text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-green-500/50"
                    />
                  </div>

                  {/* Sheet Selector for Excel */}
                  {sheets.length > 0 && (
                    <div>
                      <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                        Select Sheet
                      </label>
                      <select
                        value={selectedSheet}
                        onChange={(e) => setSelectedSheet(e.target.value)}
                        className="w-full px-3 py-2 glass-panel rounded-lg text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-green-500/50"
                      >
                        {sheets.map((sheet) => (
                          <option key={sheet} value={sheet}>
                            {sheet}
                          </option>
                        ))}
                      </select>
                    </div>
                  )}
                </div>
              )}
            </>
          )}

          {/* Uploading State */}
          {uploadState === 'uploading' && (
            <div className="py-8">
              <div className="flex items-center justify-center mb-4">
                <Loader2 className="w-12 h-12 text-green-500 animate-spin" />
              </div>
              <p className="text-center text-sm text-gray-600 dark:text-gray-300 mb-4">
                Uploading and processing...
              </p>
              <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2 overflow-hidden">
                <div
                  className="bg-green-500 h-2 rounded-full transition-all duration-300"
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
              <p className="text-center text-xs text-gray-400 mt-2">
                {uploadProgress}%
              </p>
            </div>
          )}
        </div>

        {/* Footer */}
        {(uploadState === 'idle' || uploadState === 'selecting_sheet') && selectedFile && (
          <div className="px-6 pb-6">
            <div className="flex gap-3">
              <button
                onClick={handleClose}
                className="flex-1 px-4 py-2.5 glass-panel rounded-xl text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-white/10 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleUpload}
                disabled={!selectedFile || (isExcelFile(selectedFile) && sheets.length > 0 && !selectedSheet)}
                className="flex-1 px-4 py-2.5 bg-green-500 hover:bg-green-600 text-white rounded-xl text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                <Upload className="w-4 h-4" />
                Upload File
              </button>
            </div>
          </div>
        )}

        {/* Close button for success state */}
        {uploadState === 'success' && (
          <div className="px-6 pb-6">
            <button
              onClick={handleClose}
              className="w-full px-4 py-2.5 bg-green-500 hover:bg-green-600 text-white rounded-xl text-sm font-medium transition-colors"
            >
              Done
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
