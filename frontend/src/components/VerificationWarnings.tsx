import React from 'react';

interface VerificationWarningsProps {
  warnings: string[];
}

export const VerificationWarnings: React.FC<VerificationWarningsProps> = ({ warnings }) => {
  // Don't show if no warnings
  if (!warnings || warnings.length === 0) {
    return null;
  }

  return (
    <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800/50 rounded-lg p-4 mt-4 transition-colors">
      <div className="flex items-start gap-3">
        <span className="text-2xl flex-shrink-0" role="img" aria-label="Warning">⚠️</span>
        <div className="flex-1">
          <h3 className="font-semibold text-yellow-900 dark:text-yellow-400 mb-2">
            Result Verification Warnings
          </h3>
          <div className="space-y-2">
            {warnings.map((warning, idx) => (
              <div
                key={idx}
                className="bg-yellow-100 dark:bg-yellow-900/40 border border-yellow-300 dark:border-yellow-800/50 rounded p-2"
              >
                <p className="text-sm text-yellow-900 dark:text-yellow-200">{warning}</p>
              </div>
            ))}
          </div>
          <p className="text-xs text-yellow-700 dark:text-yellow-500 mt-3">
            These warnings indicate potential issues with the query results. Please review
            the results carefully to ensure they match your expectations.
          </p>
        </div>
      </div>
    </div>
  );
};
