/**
 * useDebouncedValue - Debounces a value by a specified delay.
 *
 * Useful for search inputs to avoid triggering expensive operations on every keystroke.
 */

import { useState, useEffect } from 'react';

/**
 * Returns a debounced version of the input value.
 *
 * @param value - The value to debounce
 * @param delay - Delay in milliseconds (default: 300ms)
 * @returns The debounced value
 */
export function useDebouncedValue<T>(value: T, delay: number = 300): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(timer);
    };
  }, [value, delay]);

  return debouncedValue;
}
