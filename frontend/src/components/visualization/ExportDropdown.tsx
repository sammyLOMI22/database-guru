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
          inline-flex items-center gap-1.5 px-3.5 py-1.5 text-[13px] font-bold rounded-xl
          transition-all duration-300
          ${disabled || !hasData
            ? 'bg-gray-500/10 text-gray-400 cursor-not-allowed border-gray-500/5'
            : 'glass-card bg-white/40 dark:bg-white/10 text-gray-700 dark:text-gray-200 border-white/30 hover:bg-white/60 dark:hover:bg-white/20 hover:scale-105 select-none active:scale-95'
          }
        `}
        title={hasData ? 'Export data' : 'No data to export'}
      >
        <Download className="w-4 h-4" />
        <span className="hidden sm:inline">Export</span>
      </button>

      {/* Dropdown Menu */}
      {isOpen && hasData && (
        <div className="absolute right-0 mt-2 w-56 glass-card bg-white/95 dark:bg-gray-900/95 border-gray-500/20 rounded-2xl shadow-2xl z-50 overflow-hidden animate-scaleUp">
          <div className="py-2">
            <div className="px-4 py-2 text-[10px] font-black text-gray-500 dark:text-gray-400 uppercase tracking-[0.2em] bg-gray-500/5">
              Available Formats
            </div>
            {/* CSV Export */}
            <button
              onClick={handleExportCSV}
              className="flex items-center gap-3 w-full px-5 py-3 text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-500/10 transition-colors"
            >
              <div className="p-1.5 bg-green-500/10 rounded-lg">
                <FileSpreadsheet className="w-4 h-4 text-green-600" />
              </div>
              <span className="font-medium">Export as CSV</span>
            </button>

            {/* JSON Export */}
            <button
              onClick={handleExportJSON}
              className="flex items-center gap-3 w-full px-5 py-3 text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-500/10 transition-colors"
            >
              <div className="p-1.5 bg-blue-500/10 rounded-lg">
                <FileJson className="w-4 h-4 text-blue-600" />
              </div>
              <span className="font-medium">Export as JSON</span>
            </button>

            <div className="border-t border-gray-500/10 my-1.5 mx-2" />

            {/* Copy to Clipboard */}
            <button
              onClick={handleCopyToClipboard}
              className="flex items-center gap-3 w-full px-5 py-3 text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-500/10 transition-colors"
            >
              {copied ? (
                <div className="flex items-center gap-3 w-full text-green-600">
                  <div className="p-1.5 bg-green-500/10 rounded-lg">
                    <Check className="w-4 h-4" />
                  </div>
                  <span className="font-bold">Copied Successfully!</span>
                </div>
              ) : (
                <>
                  <div className="p-1.5 bg-gray-500/10 rounded-lg">
                    <Copy className="w-4 h-4 text-gray-500" />
                  </div>
                  <span className="font-medium">Copy Raw Results</span>
                </>
              )}
            </button>
          </div>

          {/* Row count info */}
          <div className="px-5 py-2.5 bg-gray-500/5 border-t border-gray-500/10 mt-1">
            <p className="text-[11px] text-gray-500 dark:text-gray-400 font-bold uppercase tracking-wider flex items-center justify-between">
              <span>Total Data Size</span>
              <span>{data.length.toLocaleString()} row{data.length !== 1 ? 's' : ''}</span>
            </p>
          </div>
        </div>
      )}
    </div>
  );
};

export default ExportDropdown;
