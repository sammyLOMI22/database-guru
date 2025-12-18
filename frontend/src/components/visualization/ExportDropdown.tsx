/**
 * Export Dropdown Component
 *
 * Dropdown menu for exporting data to CSV or JSON formats.
 */

import React, { useState, useRef, useEffect } from 'react';
import { Download, FileSpreadsheet, FileJson, Check, Copy } from 'lucide-react';
import { exportToCSV, exportToJSON, copyToClipboard, JSONExportMetadata } from '../../utils/exportUtils';

interface ExportDropdownProps {
  data: Record<string, unknown>[];
  sql?: string;
  question?: string;
  connectionName?: string;
  databaseType?: string;
  disabled?: boolean;
}

export const ExportDropdown: React.FC<ExportDropdownProps> = ({
  data,
  sql,
  question,
  connectionName,
  databaseType,
  disabled = false,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleExportCSV = () => {
    exportToCSV(data);
    setIsOpen(false);
  };

  const handleExportJSON = () => {
    const metadata: JSONExportMetadata = {
      query: question,
      sql: sql,
      timestamp: new Date().toISOString(),
      rowCount: data.length,
      connectionName,
      databaseType,
    };
    exportToJSON(data, metadata);
    setIsOpen(false);
  };

  const handleCopyToClipboard = async () => {
    const success = await copyToClipboard(data);
    if (success) {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
    setIsOpen(false);
  };

  const hasData = data && data.length > 0;

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Export Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        disabled={disabled || !hasData}
        className={`
          inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-lg
          border transition-all duration-150
          ${
            disabled || !hasData
              ? 'bg-gray-100 text-gray-400 border-gray-200 cursor-not-allowed'
              : 'bg-white text-gray-700 border-gray-200 hover:bg-gray-50 hover:border-gray-300'
          }
        `}
        title={hasData ? 'Export data' : 'No data to export'}
      >
        <Download className="w-4 h-4" />
        <span className="hidden sm:inline">Export</span>
      </button>

      {/* Dropdown Menu */}
      {isOpen && hasData && (
        <div className="absolute right-0 mt-1 w-48 rounded-lg bg-white border border-gray-200 shadow-lg z-50">
          <div className="py-1">
            {/* CSV Export */}
            <button
              onClick={handleExportCSV}
              className="flex items-center gap-3 w-full px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
            >
              <FileSpreadsheet className="w-4 h-4 text-green-600" />
              <span>Export as CSV</span>
            </button>

            {/* JSON Export */}
            <button
              onClick={handleExportJSON}
              className="flex items-center gap-3 w-full px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
            >
              <FileJson className="w-4 h-4 text-blue-600" />
              <span>Export as JSON</span>
            </button>

            <div className="border-t border-gray-100 my-1" />

            {/* Copy to Clipboard */}
            <button
              onClick={handleCopyToClipboard}
              className="flex items-center gap-3 w-full px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
            >
              {copied ? (
                <>
                  <Check className="w-4 h-4 text-green-600" />
                  <span className="text-green-600">Copied!</span>
                </>
              ) : (
                <>
                  <Copy className="w-4 h-4 text-gray-500" />
                  <span>Copy to Clipboard</span>
                </>
              )}
            </button>
          </div>

          {/* Row count info */}
          <div className="px-4 py-2 bg-gray-50 border-t border-gray-100 rounded-b-lg">
            <p className="text-xs text-gray-500">
              {data.length.toLocaleString()} row{data.length !== 1 ? 's' : ''}
            </p>
          </div>
        </div>
      )}
    </div>
  );
};

export default ExportDropdown;
