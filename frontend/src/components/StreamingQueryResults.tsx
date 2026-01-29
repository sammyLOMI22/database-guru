import { useState, useEffect } from 'react';
import { queryAPI } from '../services/api';
import type { QueryRequest } from '../types/api';
import { useTableSort } from '../hooks/useTableSort';
import { SortableTableHeader } from './SortableTableHeader';

interface StreamingQueryResultsProps {
  request: QueryRequest;
  onComplete?: () => void;
  onError?: (error: string) => void;
}

interface StreamingState {
  status: 'idle' | 'generating_sql' | 'executing' | 'streaming' | 'complete' | 'error';
  statusMessage: string;
  sql: string | null;
  usedContext: boolean;
  columns: string[];
  rows: any[];
  batchNumber: number;
  rowsReceived: number;
  totalRows: number | null;
  executionTimeMs: number | null;
  truncated: boolean;
  error: string | null;
}

export default function StreamingQueryResults({ request, onComplete, onError }: StreamingQueryResultsProps) {
  const [state, setState] = useState<StreamingState>({
    status: 'idle',
    statusMessage: '',
    sql: null,
    usedContext: false,
    columns: [],
    rows: [],
    batchNumber: 0,
    rowsReceived: 0,
    totalRows: null,
    executionTimeMs: null,
    truncated: false,
    error: null,
  });

  // Sorting - only enabled after streaming completes
  const { sortedData, sortConfig, handleSort, resetSort } = useTableSort(
    state.rows,
    {} // No onSortChange needed since there's no pagination
  );

  // Sorting is only enabled when streaming is complete
  const sortingEnabled = state.status === 'complete';

  useEffect(() => {
    // Reset sort when a new request starts
    resetSort();
    startStreaming();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- resetSort is stable, intentionally omitted to avoid re-triggering on its changes
  }, [request]);

  const startStreaming = async () => {
    try {
      await queryAPI.streamQuery(request, {
        onStatus: (data) => {
          setState(prev => ({
            ...prev,
            status: data.status as any,
            statusMessage: data.message,
          }));
        },

        onSqlGenerated: (data) => {
          setState(prev => ({
            ...prev,
            status: 'executing',
            sql: data.sql,
            usedContext: data.used_context,
          }));
        },

        onMetadata: (data) => {
          setState(prev => ({
            ...prev,
            status: 'streaming',
            columns: data.columns,
          }));
        },

        onData: (data) => {
          setState(prev => ({
            ...prev,
            rows: [...prev.rows, ...data.data],
            batchNumber: data.batch_number,
            rowsReceived: data.rows_sent,
          }));
        },

        onComplete: (data) => {
          setState(prev => ({
            ...prev,
            status: 'complete',
            totalRows: data.total_rows,
            executionTimeMs: data.execution_time_ms,
            truncated: data.truncated,
          }));
          onComplete?.();
        },

        onError: (error) => {
          setState(prev => ({
            ...prev,
            status: 'error',
            error,
          }));
          onError?.(error);
        },
      });
    } catch (error: any) {
      setState(prev => ({
        ...prev,
        status: 'error',
        error: error.message || 'Stream error',
      }));
      onError?.(error.message || 'Stream error');
    }
  };

  // Progress percentage calculation
  const progressPercentage = state.totalRows
    ? Math.min(100, (state.rowsReceived / state.totalRows) * 100)
    : state.rowsReceived > 0
    ? 50
    : 0;

  return (
    <div className="w-full space-y-4">
      {/* Status Indicator */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center space-x-2">
            {state.status === 'generating_sql' && (
              <>
                <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
                <span className="text-sm font-medium text-gray-700">Generating SQL...</span>
              </>
            )}
            {state.status === 'executing' && (
              <>
                <div className="w-4 h-4 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
                <span className="text-sm font-medium text-gray-700">Executing query...</span>
              </>
            )}
            {state.status === 'streaming' && (
              <>
                <div className="w-4 h-4 border-2 border-green-500 border-t-transparent rounded-full animate-spin" />
                <span className="text-sm font-medium text-gray-700">Streaming results...</span>
              </>
            )}
            {state.status === 'complete' && (
              <>
                <svg className="w-4 h-4 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
                <span className="text-sm font-medium text-green-700">Complete!</span>
              </>
            )}
            {state.status === 'error' && (
              <>
                <svg className="w-4 h-4 text-red-500" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
                <span className="text-sm font-medium text-red-700">Error</span>
              </>
            )}
          </div>

          {/* Row counter */}
          {state.rowsReceived > 0 && (
            <div className="text-sm text-gray-600">
              {state.rowsReceived.toLocaleString()} rows
              {state.totalRows && ` of ${state.totalRows.toLocaleString()}`}
            </div>
          )}
        </div>

        {/* Progress bar */}
        {state.status === 'streaming' && (
          <div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
            <div
              className="bg-gradient-to-r from-blue-500 to-indigo-500 h-2 transition-all duration-300 ease-out"
              style={{ width: `${progressPercentage}%` }}
            />
          </div>
        )}

        {/* Status message */}
        {state.statusMessage && (
          <p className="text-xs text-gray-500 mt-2">{state.statusMessage}</p>
        )}
      </div>

      {/* SQL Display */}
      {state.sql && (
        <div className="bg-gray-900 rounded-lg p-4 text-sm">
          <div className="flex items-center justify-between mb-2">
            <span className="text-gray-400 text-xs font-mono">SQL</span>
            {state.usedContext && (
              <span className="text-xs bg-blue-500/20 text-blue-300 px-2 py-1 rounded">
                Using conversation context
              </span>
            )}
          </div>
          <pre className="text-gray-100 font-mono overflow-x-auto whitespace-pre-wrap">
            {state.sql}
          </pre>
        </div>
      )}

      {/* Error Display */}
      {state.error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex items-start">
            <svg className="w-5 h-5 text-red-500 mt-0.5 mr-2" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
            </svg>
            <div>
              <h4 className="text-sm font-medium text-red-800">Error occurred</h4>
              <p className="text-sm text-red-700 mt-1">{state.error}</p>
            </div>
          </div>
        </div>
      )}

      {/* Results Table - Progressive Rendering */}
      {state.columns.length > 0 && (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
          {/* Table header with stats */}
          <div className="px-4 py-3 bg-gray-50 border-b border-gray-200">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-medium text-gray-900">Results</h3>
              <div className="flex items-center space-x-4 text-xs text-gray-500">
                {state.executionTimeMs && (
                  <span>{state.executionTimeMs.toFixed(0)}ms</span>
                )}
                {state.truncated && (
                  <span className="bg-yellow-100 text-yellow-800 px-2 py-1 rounded">
                    Truncated (max 1000 rows)
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* Table */}
          <div className="overflow-x-auto max-h-96">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50 sticky top-0">
                <tr>
                  {state.columns.map((column, idx) => (
                    <SortableTableHeader
                      key={idx}
                      column={column}
                      sortConfig={sortConfig}
                      onSort={handleSort}
                      disabled={!sortingEnabled}
                      className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider hover:bg-gray-100 transition-colors"
                    />
                  ))}
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {sortedData.map((row, rowIdx) => (
                  <tr
                    key={rowIdx}
                    className={`${
                      rowIdx % 2 === 0 ? 'bg-white' : 'bg-gray-50'
                    } hover:bg-blue-50 transition-colors animate-fadeIn`}
                  >
                    {state.columns.map((column, colIdx) => (
                      <td
                        key={colIdx}
                        className="px-4 py-3 whitespace-nowrap text-sm text-gray-900"
                      >
                        {row[column] === null ? (
                          <span className="text-gray-400 italic">null</span>
                        ) : typeof row[column] === 'object' ? (
                          <span className="text-gray-600 font-mono text-xs">
                            {JSON.stringify(row[column])}
                          </span>
                        ) : (
                          String(row[column])
                        )}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Streaming indicator at bottom */}
          {state.status === 'streaming' && (
            <div className="px-4 py-2 bg-blue-50 border-t border-blue-100">
              <div className="flex items-center justify-center text-xs text-blue-600">
                <div className="w-3 h-3 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mr-2" />
                Loading more rows... (Batch {state.batchNumber})
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
