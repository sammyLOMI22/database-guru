/**
 * LineageNarrative - Phase 12.1
 *
 * Displays LLM-generated narrative explanations of data lineage.
 * Shows summary, column explanations, and potential issues.
 */
import { useState } from 'react';
import { FileText, ChevronDown, ChevronUp, AlertTriangle, BookOpen, Zap } from 'lucide-react';
import type { LineageNarrative as LineageNarrativeType } from '../../types/lineage';

interface LineageNarrativeProps {
  narrative: LineageNarrativeType | null | undefined;
  isLoading?: boolean;
}

export function LineageNarrative({ narrative, isLoading = false }: LineageNarrativeProps) {
  const [showDetails, setShowDetails] = useState(false);

  if (isLoading) {
    return (
      <div className="bg-blue-50 dark:bg-blue-900/20 rounded-xl p-4 border border-blue-200 dark:border-blue-800">
        <div className="flex items-center gap-3">
          <div className="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
          <span className="text-sm font-medium text-blue-600 dark:text-blue-400">
            Generating explanation...
          </span>
        </div>
      </div>
    );
  }

  if (!narrative) {
    return null;
  }

  const confidenceColor = narrative.confidence >= 0.7
    ? 'text-green-600 dark:text-green-400'
    : narrative.confidence >= 0.5
    ? 'text-yellow-600 dark:text-yellow-400'
    : 'text-red-600 dark:text-red-400';

  const confidenceLabel = narrative.confidence >= 0.7
    ? 'High'
    : narrative.confidence >= 0.5
    ? 'Medium'
    : 'Low';

  return (
    <div className="bg-blue-50 dark:bg-blue-900/20 rounded-xl border border-blue-200 dark:border-blue-800 overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 bg-blue-100/50 dark:bg-blue-900/30 border-b border-blue-200 dark:border-blue-800">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <FileText className="w-4 h-4 text-blue-600 dark:text-blue-400" />
            <span className="text-xs font-black uppercase tracking-widest text-blue-700 dark:text-blue-300">
              Data Flow Explanation
            </span>
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-600 dark:text-blue-400 font-bold uppercase tracking-widest">
              AI Generated
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span className={`text-[10px] font-bold uppercase tracking-widest ${confidenceColor}`}>
              {confidenceLabel} Confidence ({Math.round(narrative.confidence * 100)}%)
            </span>
          </div>
        </div>
      </div>

      {/* Summary */}
      <div className="p-4">
        <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">
          {narrative.summary}
        </p>

        {/* Data Flow Description (if provided) */}
        {narrative.data_flow_description && (
          <div className="mt-3 p-3 bg-white/50 dark:bg-gray-800/50 rounded-lg border border-blue-100 dark:border-blue-900">
            <div className="flex items-center gap-2 mb-2">
              <Zap className="w-3.5 h-3.5 text-indigo-500" />
              <span className="text-[10px] font-bold uppercase tracking-widest text-indigo-600 dark:text-indigo-400">
                Data Flow
              </span>
            </div>
            <p className="text-xs text-gray-600 dark:text-gray-400 leading-relaxed">
              {narrative.data_flow_description}
            </p>
          </div>
        )}

        {/* Toggle for details */}
        <button
          onClick={() => setShowDetails(!showDetails)}
          className="mt-3 flex items-center gap-1 text-xs font-medium text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 transition-colors"
        >
          {showDetails ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          {showDetails ? 'Hide Details' : 'Show Column Details'}
        </button>

        {/* Details Section */}
        {showDetails && (
          <div className="mt-4 space-y-4">
            {/* Column Explanations */}
            {Object.keys(narrative.column_explanations).length > 0 && (
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <BookOpen className="w-3.5 h-3.5 text-emerald-500" />
                  <span className="text-[10px] font-bold uppercase tracking-widest text-emerald-600 dark:text-emerald-400">
                    Output Columns
                  </span>
                </div>
                <div className="space-y-2">
                  {Object.entries(narrative.column_explanations).map(([col, explanation]) => (
                    <div
                      key={col}
                      className="flex items-start gap-2 p-2 bg-white/50 dark:bg-gray-800/50 rounded-lg"
                    >
                      <code className="text-xs font-mono px-1.5 py-0.5 bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400 rounded">
                        {col}
                      </code>
                      <span className="text-xs text-gray-600 dark:text-gray-400">
                        {explanation}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Business Context */}
            {Object.keys(narrative.business_context).length > 0 && (
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-[10px] font-bold uppercase tracking-widest text-purple-600 dark:text-purple-400">
                    Business Terms
                  </span>
                </div>
                <div className="flex flex-wrap gap-2">
                  {Object.entries(narrative.business_context).map(([technical, business]) => (
                    <span
                      key={technical}
                      className="inline-flex items-center gap-1 text-xs px-2 py-1 bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-400 rounded-lg"
                    >
                      <span className="font-mono">{technical}</span>
                      <span className="text-purple-400 dark:text-purple-500">=</span>
                      <span className="font-medium">{business}</span>
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Transformation Explanations */}
            {narrative.transformations_explained.length > 0 && (
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-[10px] font-bold uppercase tracking-widest text-orange-600 dark:text-orange-400">
                    Transformations
                  </span>
                </div>
                <div className="space-y-2">
                  {narrative.transformations_explained.map((trans, i) => (
                    <div
                      key={trans.node_id || i}
                      className="p-2 bg-white/50 dark:bg-gray-800/50 rounded-lg"
                    >
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-[10px] px-1.5 py-0.5 bg-orange-100 dark:bg-orange-900/30 text-orange-600 dark:text-orange-400 rounded font-bold uppercase">
                          {trans.transformation_type}
                        </span>
                        <span className="text-xs text-gray-500 dark:text-gray-500">
                          {trans.output_column}
                        </span>
                      </div>
                      <p className="text-xs text-gray-600 dark:text-gray-400">
                        {trans.explanation}
                      </p>
                      {trans.business_meaning && (
                        <p className="text-xs text-purple-600 dark:text-purple-400 mt-1 italic">
                          Business meaning: {trans.business_meaning}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Potential Issues */}
        {narrative.potential_issues.length > 0 && (
          <div className="mt-4 p-3 bg-amber-50 dark:bg-amber-900/20 rounded-lg border border-amber-200 dark:border-amber-800">
            <div className="flex items-center gap-2 mb-2">
              <AlertTriangle className="w-3.5 h-3.5 text-amber-600 dark:text-amber-400" />
              <span className="text-[10px] font-bold uppercase tracking-widest text-amber-700 dark:text-amber-400">
                Potential Issues
              </span>
            </div>
            <ul className="space-y-1">
              {narrative.potential_issues.map((issue, i) => (
                <li key={i} className="text-xs text-amber-700 dark:text-amber-400 flex items-start gap-2">
                  <span className="text-amber-400">•</span>
                  {issue}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}

export default LineageNarrative;
