import React, { useState } from 'react';

interface SQLEditorProps {
  initialSQL: string;
  readOnly?: boolean;
  onChange?: (sql: string) => void;
  label?: string;
}

export const SQLEditor: React.FC<SQLEditorProps> = ({
  initialSQL,
  readOnly = false,
  onChange,
  label
}) => {
  const [sql, setSQL] = useState(initialSQL);

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const newSQL = e.target.value;
    setSQL(newSQL);
    onChange?.(newSQL);
  };

  return (
    <div className="sql-editor">
      {label && (
        <label className="block font-semibold text-gray-900 mb-2">
          {label}
        </label>
      )}
      <textarea
        value={sql}
        onChange={handleChange}
        readOnly={readOnly}
        className={`
          w-full p-4 font-mono text-sm
          border rounded-lg
          min-h-[200px]
          focus:outline-none focus:ring-2 focus:ring-blue-500
          ${readOnly ? 'bg-gray-50 cursor-not-allowed text-gray-700' : 'bg-white'}
        `}
        spellCheck={false}
        placeholder="Enter SQL query..."
      />
    </div>
  );
};
