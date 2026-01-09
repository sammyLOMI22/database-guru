import React, { useState } from 'react';
import type { ValidateMultiDBResponse, DatabaseAssessmentResponse } from '../types/api';
import { QueryFeasibilityBadge } from './QueryFeasibilityBadge';

interface MultiDatabaseAssessmentProps {
  validation: ValidateMultiDBResponse;
  onProceed?: (selectedIds: number[]) => void;
  onCancel?: () => void;
}

export const MultiDatabaseAssessment: React.FC<MultiDatabaseAssessmentProps> = ({
  validation,
  onProceed,
  onCancel,
}) => {
  // Initialize with all executable databases selected
  const [selectedIds, setSelectedIds] = useState<Set<number>>(() => {
    const executable = validation.assessments
      .filter((a) => a.capability !== 'cannot')
      .map((a) => a.connection_id);
    return new Set(executable);
  });

  const summary = {
    full: validation.assessments.filter((a) => a.capability === 'full').length,
    partial: validation.assessments.filter((a) => a.capability === 'partial').length,
    cannot: validation.assessments.filter((a) => a.capability === 'cannot').length,
  };

  const toggleSelection = (id: number, capability: string) => {
    if (capability === 'cannot') return; // Cannot toggle non-executable databases

    const newSelected = new Set(selectedIds);
    if (newSelected.has(id)) {
      newSelected.delete(id);
    } else {
      newSelected.add(id);
    }
    setSelectedIds(newSelected);
  };

  const selectAll = () => {
    const executable = validation.assessments
      .filter((a) => a.capability !== 'cannot')
      .map((a) => a.connection_id);
    setSelectedIds(new Set(executable));
  };

  const selectNone = () => {
    setSelectedIds(new Set());
  };

  const handleProceed = () => {
    if (onProceed && selectedIds.size > 0) {
      onProceed(Array.from(selectedIds));
    }
  };

  return (
    <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-200 bg-gray-50 rounded-t-lg">
        <h3 className="text-lg font-semibold text-gray-900">
          Query Feasibility Assessment
        </h3>
        <p className="text-sm text-gray-600 mt-1">
          Review which databases can execute this query
        </p>
      </div>

      {/* Summary Section */}
      <div className="px-4 py-3 border-b border-gray-100 bg-gray-50/50">
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-green-500" />
            <span className="text-sm text-gray-700">
              <span className="font-semibold">{summary.full}</span> Full
            </span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-yellow-500" />
            <span className="text-sm text-gray-700">
              <span className="font-semibold">{summary.partial}</span> Partial
            </span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-red-500" />
            <span className="text-sm text-gray-700">
              <span className="font-semibold">{summary.cannot}</span> Cannot
            </span>
          </div>
        </div>

        {/* Overall Status */}
        <div className="mt-2">
          {validation.all_full ? (
            <span className="inline-flex items-center gap-1 text-sm text-green-700 bg-green-100 px-2 py-1 rounded">
              <span>✓</span> All databases can execute this query
            </span>
          ) : validation.can_execute_any ? (
            <span className="inline-flex items-center gap-1 text-sm text-yellow-700 bg-yellow-100 px-2 py-1 rounded">
              <span>⚡</span> Some databases may need query modifications
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 text-sm text-red-700 bg-red-100 px-2 py-1 rounded">
              <span>✗</span> No databases can execute this query
            </span>
          )}
        </div>
      </div>

      {/* Warnings */}
      {validation.warnings.length > 0 && (
        <div className="px-4 py-2 bg-amber-50 border-b border-amber-100">
          {validation.warnings.map((warning, idx) => (
            <div key={idx} className="flex items-start gap-2 text-sm text-amber-800">
              <span>⚠️</span>
              <span>{warning}</span>
            </div>
          ))}
        </div>
      )}

      {/* Database List */}
      <div className="px-4 py-3">
        <div className="flex items-center justify-between mb-3">
          <span className="text-sm font-medium text-gray-700">
            Select databases to query:
          </span>
          <div className="flex gap-2">
            <button
              onClick={selectAll}
              className="text-xs text-blue-600 hover:text-blue-800"
            >
              Select All
            </button>
            <span className="text-gray-300">|</span>
            <button
              onClick={selectNone}
              className="text-xs text-blue-600 hover:text-blue-800"
            >
              Select None
            </button>
          </div>
        </div>

        <div className="space-y-3">
          {validation.assessments.map((assessment) => (
            <DatabaseAssessmentRow
              key={assessment.connection_id}
              assessment={assessment}
              selected={selectedIds.has(assessment.connection_id)}
              onToggle={() => toggleSelection(assessment.connection_id, assessment.capability)}
            />
          ))}
        </div>
      </div>

      {/* Actions */}
      <div className="px-4 py-3 border-t border-gray-200 bg-gray-50 rounded-b-lg flex justify-end gap-3">
        {onCancel && (
          <button
            onClick={onCancel}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
          >
            Cancel
          </button>
        )}
        {onProceed && (
          <button
            onClick={handleProceed}
            disabled={selectedIds.size === 0}
            className={`px-4 py-2 text-sm font-medium text-white rounded-md ${
              selectedIds.size === 0
                ? 'bg-gray-400 cursor-not-allowed'
                : 'bg-blue-600 hover:bg-blue-700'
            }`}
          >
            Proceed with {selectedIds.size} Database{selectedIds.size !== 1 ? 's' : ''}
          </button>
        )}
      </div>
    </div>
  );
};

interface DatabaseAssessmentRowProps {
  assessment: DatabaseAssessmentResponse;
  selected: boolean;
  onToggle: () => void;
}

const DatabaseAssessmentRow: React.FC<DatabaseAssessmentRowProps> = ({
  assessment,
  selected,
  onToggle,
}) => {
  const isDisabled = assessment.capability === 'cannot';

  return (
    <div
      className={`flex items-start gap-3 p-3 rounded-lg border ${
        isDisabled
          ? 'bg-gray-50 border-gray-200 opacity-60'
          : selected
          ? 'bg-blue-50 border-blue-200'
          : 'bg-white border-gray-200 hover:bg-gray-50'
      }`}
    >
      {/* Checkbox */}
      <div className="flex items-center h-5 mt-0.5">
        <input
          type="checkbox"
          checked={selected}
          onChange={onToggle}
          disabled={isDisabled}
          className={`h-4 w-4 rounded ${
            isDisabled
              ? 'text-gray-400 cursor-not-allowed'
              : 'text-blue-600 cursor-pointer'
          } border-gray-300 focus:ring-blue-500`}
        />
      </div>

      {/* Database Info */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <span className="font-medium text-gray-900 truncate">
            {assessment.connection_name}
          </span>
          <span className="text-xs text-gray-500 px-1.5 py-0.5 bg-gray-100 rounded">
            {assessment.database_type}
          </span>
        </div>
        <p className="text-sm text-gray-600 mb-2">
          {assessment.reason}
        </p>

        {/* Alternatives hint */}
        {Object.keys(assessment.available_alternatives).length > 0 && (
          <div className="text-xs text-yellow-700 bg-yellow-50 px-2 py-1 rounded inline-block">
            Will use alternatives: {Object.entries(assessment.available_alternatives)
              .map(([from, to]) => `${from.split('.').pop()} → ${to}`)
              .join(', ')}
          </div>
        )}

        {/* Missing info hint */}
        {assessment.missing_tables.length > 0 && (
          <div className="text-xs text-red-700 bg-red-50 px-2 py-1 rounded inline-block">
            Missing tables: {assessment.missing_tables.join(', ')}
          </div>
        )}
      </div>

      {/* Badge */}
      <div className="flex-shrink-0">
        <QueryFeasibilityBadge assessment={assessment} compact />
      </div>
    </div>
  );
};

export default MultiDatabaseAssessment;
