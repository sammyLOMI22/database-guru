import React from 'react';
import { ArrowUp, ArrowDown, ArrowUpDown } from 'lucide-react';
import type { SortConfig } from '../hooks/useTableSort';

export interface SortableTableHeaderProps {
  /** Column key/identifier */
  column: string;
  /** Display label (defaults to column if not provided) */
  label?: string;
  /** Current sort configuration */
  sortConfig: SortConfig;
  /** Callback when header is clicked */
  onSort: (column: string) => void;
  /** Additional CSS classes for the th element */
  className?: string;
  /** Whether sorting is disabled (e.g., during streaming) */
  disabled?: boolean;
}

/**
 * A sortable table header component with visual indicators and keyboard accessibility
 *
 * @example
 * ```tsx
 * <SortableTableHeader
 *   column="name"
 *   label="Full Name"
 *   sortConfig={sortConfig}
 *   onSort={handleSort}
 *   className="px-4 py-2"
 * />
 * ```
 */
export function SortableTableHeader({
  column,
  label,
  sortConfig,
  onSort,
  className = '',
  disabled = false,
}: SortableTableHeaderProps) {
  const isActive = sortConfig.column === column;
  const direction = isActive ? sortConfig.direction : null;

  const handleClick = () => {
    if (!disabled) {
      onSort(column);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!disabled && (e.key === 'Enter' || e.key === ' ')) {
      e.preventDefault();
      onSort(column);
    }
  };

  // Determine aria-sort value
  const ariaSort: 'ascending' | 'descending' | 'none' =
    direction === 'asc'
      ? 'ascending'
      : direction === 'desc'
        ? 'descending'
        : 'none';

  // Select the appropriate icon based on sort state
  const SortIcon = direction === 'asc'
    ? ArrowUp
    : direction === 'desc'
      ? ArrowDown
      : ArrowUpDown;

  return (
    <th
      role="columnheader"
      aria-sort={ariaSort}
      tabIndex={disabled ? -1 : 0}
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      className={`
        ${className}
        ${disabled ? 'cursor-default' : 'cursor-pointer select-none'}
        group
      `}
    >
      <div className="flex items-center gap-1">
        <span>{label ?? column}</span>
        <SortIcon
          className={`
            w-3 h-3 flex-shrink-0 transition-opacity
            ${isActive
              ? 'opacity-100 text-indigo-400'
              : 'opacity-0 group-hover:opacity-50 text-gray-400'
            }
            ${disabled ? 'hidden' : ''}
          `}
        />
      </div>
    </th>
  );
}
