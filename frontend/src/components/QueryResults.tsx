import { Copy, Check } from 'lucide-react';
import { useState } from 'react';

interface QueryResultsProps {
  sql: string;
  results: Record<string, any>[] | null;
  rowCount: number | null;
  executionTime: number | null;
  isValid: boolean;
  warnings: string[];
}

export default function QueryResults({
  sql,
  results,
  rowCount,
  executionTime,
  isValid,
  warnings,
}: QueryResultsProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(sql);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="space-y-4">
      {/* SQL Display */}
      <div className="bg-gray-900 rounded-lg p-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-medium text-gray-400 uppercase">Generated SQL</span>
          <button
            onClick={handleCopy}
            className="text-gray-400 hover:text-white transition-colors p-1"
            title="Copy SQL"
          >
            {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
          </button>
        </div>
        <pre className="text-sm text-green-400 font-mono overflow-x-auto">
          {sql}
        </pre>
      </div>

      {/* Warnings */}
      {warnings.length > 0 && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <div className="flex items-start space-x-2">
            <span className="text-yellow-600">⚠️</span>
            <div className="flex-1">
              <p className="text-sm font-medium text-yellow-800">Warnings:</p>
              <ul className="mt-1 text-sm text-yellow-700 list-disc list-inside">
                {warnings.map((warning, index) => (
                  <li key={index}>{warning}</li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* Results */}
      {results && results.length > 0 ? (
        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          {/* Header with stats */}
          <div className="px-4 py-3 bg-gray-50 border-b border-gray-200 flex items-center justify-between">
            <div className="flex items-center space-x-4 text-sm text-gray-600">
              <span>
                <strong className="text-gray-900">{rowCount}</strong> rows
              </span>
              {executionTime !== null && (
                <span>
                  <strong className="text-gray-900">{executionTime.toFixed(2)}</strong> ms
                </span>
              )}
            </div>
          </div>

          {/* Table */}
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  {Object.keys(results[0]).map((column) => (
                    <th
                      key={column}
                      className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider"
                    >
                      {column}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {results.map((row, rowIndex) => (
                  <tr
                    key={rowIndex}
                    className="hover:bg-gray-50 transition-colors"
                  >
                    {Object.values(row).map((value, colIndex) => (
                      <td
                        key={colIndex}
                        className="px-4 py-3 text-sm text-gray-900 font-mono"
                      >
                        {value === null ? (
                          <span className="text-gray-400 italic">null</span>
                        ) : typeof value === 'object' ? (
                          JSON.stringify(value)
                        ) : (
                          String(value)
                        )}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <div className="bg-gray-50 rounded-lg p-8 text-center">
          <p className="text-gray-500">
            {isValid ? 'No results returned' : 'Query could not be executed'}
          </p>
        </div>
      )}
    </div>
  );
}
