/**
 * Combined Export Dropdown Component
 *
 * Provides export options for multi-database query results:
 * - Stacked CSV: All rows merged with database_name column
 * - Stacked JSON: Combined JSON with database metadata
 * - Separate Files (ZIP): Individual files per database
 */

import { useState, useRef, useEffect } from 'react';
import { Download, ChevronDown, FileText, FileJson, FolderArchive } from 'lucide-react';
import {
  exportCombinedCSV,
  exportCombinedJSON,
  exportSeparateFiles,
  DatabaseResultForExport,
} from '../../utils/exportUtils';

interface CombinedExportDropdownProps {
  results: DatabaseResultForExport[];
  question?: string;
  disabled?: boolean;
}

type ExportMode = 'stacked' | 'separate';

export function CombinedExportDropdown({
  results,
  question,
  disabled = false,
}: CombinedExportDropdownProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [exportMode, setExportMode] = useState<ExportMode>('stacked');
  const [isExporting, setIsExporting] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Calculate total rows across all successful results
  const successfulResults = results.filter(
    (r) => r.success && r.results && r.results.length > 0
  );
  const totalRows = successfulResults.reduce(
    (sum, r) => sum + (r.results?.length || 0),
    0
  );
  const hasData = totalRows > 0;

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleExportCSV = () => {
    if (exportMode === 'stacked') {
      exportCombinedCSV(results);
    } else {
      setIsExporting(true);
      exportSeparateFiles(results, 'csv').finally(() => setIsExporting(false));
    }
    setIsOpen(false);
  };

  const handleExportJSON = () => {
    if (exportMode === 'stacked') {
      exportCombinedJSON(results, question);
    } else {
      setIsExporting(true);
      exportSeparateFiles(results, 'json').finally(() => setIsExporting(false));
    }
    setIsOpen(false);
  };

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        disabled={disabled || !hasData || isExporting}
        className={`
          flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium
          transition-colors
          ${
            disabled || !hasData
              ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
              : 'bg-blue-500 text-white hover:bg-blue-600'
          }
        `}
        title={!hasData ? 'No data to export' : 'Export all database results'}
      >
        <Download className="w-4 h-4" />
        <span>Export All</span>
        <ChevronDown className={`w-4 h-4 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {isOpen && (
        <div className="absolute right-0 mt-1 w-64 bg-white border border-gray-200 rounded-lg shadow-lg z-50">
          {/* Header with row count */}
          <div className="px-3 py-2 border-b border-gray-100 bg-gray-50 rounded-t-lg">
            <p className="text-xs text-gray-600">
              {totalRows.toLocaleString()} row{totalRows !== 1 ? 's' : ''} from{' '}
              {successfulResults.length} database{successfulResults.length !== 1 ? 's' : ''}
            </p>
          </div>

          {/* Export mode selection */}
          <div className="px-3 py-2 border-b border-gray-100">
            <p className="text-xs font-medium text-gray-700 mb-2">Export Mode</p>
            <div className="space-y-1">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="exportMode"
                  value="stacked"
                  checked={exportMode === 'stacked'}
                  onChange={() => setExportMode('stacked')}
                  className="w-3.5 h-3.5 text-blue-500"
                />
                <span className="text-sm text-gray-700">
                  Stacked <span className="text-gray-500">(single file)</span>
                </span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="exportMode"
                  value="separate"
                  checked={exportMode === 'separate'}
                  onChange={() => setExportMode('separate')}
                  className="w-3.5 h-3.5 text-blue-500"
                />
                <span className="text-sm text-gray-700">
                  Separate Files <span className="text-gray-500">(ZIP)</span>
                </span>
              </label>
            </div>
          </div>

          {/* Export options */}
          <div className="py-1">
            <button
              onClick={handleExportCSV}
              className="w-full px-3 py-2 text-left text-sm text-gray-700 hover:bg-gray-50 flex items-center gap-2"
            >
              {exportMode === 'separate' ? (
                <FolderArchive className="w-4 h-4 text-gray-400" />
              ) : (
                <FileText className="w-4 h-4 text-gray-400" />
              )}
              <span>
                Export as CSV{exportMode === 'stacked' && ' (with database_name column)'}
              </span>
            </button>
            <button
              onClick={handleExportJSON}
              className="w-full px-3 py-2 text-left text-sm text-gray-700 hover:bg-gray-50 flex items-center gap-2"
            >
              {exportMode === 'separate' ? (
                <FolderArchive className="w-4 h-4 text-gray-400" />
              ) : (
                <FileJson className="w-4 h-4 text-gray-400" />
              )}
              <span>Export as JSON</span>
            </button>
          </div>

          {/* Mode description */}
          <div className="px-3 py-2 border-t border-gray-100 bg-gray-50 rounded-b-lg">
            <p className="text-xs text-gray-500">
              {exportMode === 'stacked'
                ? 'All rows combined in one file with source column'
                : 'One file per database in a ZIP archive'}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
