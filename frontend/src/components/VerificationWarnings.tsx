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
    <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mt-4">
      <div className="flex items-start gap-3">
        <span className="text-2xl flex-shrink-0" role="img" aria-label="Warning">⚠️</span>
        <div className="flex-1">
          <h3 className="font-semibold text-yellow-900 mb-2">
            Result Verification Warnings
          </h3>
          <div className="space-y-2">
            {warnings.map((warning, idx) => (
              <div
                key={idx}
                className="bg-yellow-100 border border-yellow-300 rounded p-2"
              >
                <p className="text-sm text-yellow-900">{warning}</p>
              </div>
            ))}
          </div>
          <p className="text-xs text-yellow-700 mt-3">
            These warnings indicate potential issues with the query results. Please review
            the results carefully to ensure they match your expectations.
          </p>
        </div>
      </div>
    </div>
  );
};
