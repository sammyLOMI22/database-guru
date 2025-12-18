/**
 * Chart Preferences Hook
 *
 * Manages user preferences for chart visualization, persisted in localStorage.
 */

import { useState, useCallback, useEffect } from 'react';
import { ChartType } from '../utils/chartUtils';

export type ViewMode = 'table' | 'chart';

export interface ChartPreferences {
  defaultViewMode: ViewMode;
  preferredChartHeight: number;
  showChartLegend: boolean;
  chartAnimations: boolean;
}

const STORAGE_KEY = 'dbguru-chart-prefs';

const DEFAULT_PREFERENCES: ChartPreferences = {
  defaultViewMode: 'table',
  preferredChartHeight: 300,
  showChartLegend: true,
  chartAnimations: true,
};

/**
 * Loads preferences from localStorage
 */
function loadPreferences(): ChartPreferences {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      const parsed = JSON.parse(stored);
      // Merge with defaults to handle new fields
      return { ...DEFAULT_PREFERENCES, ...parsed };
    }
  } catch (error) {
    console.warn('Failed to load chart preferences:', error);
  }
  return DEFAULT_PREFERENCES;
}

/**
 * Saves preferences to localStorage
 */
function savePreferences(preferences: ChartPreferences): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(preferences));
  } catch (error) {
    console.warn('Failed to save chart preferences:', error);
  }
}

/**
 * Hook for managing chart visualization preferences
 *
 * @returns Preferences object and update function
 */
export function useChartPreferences() {
  const [preferences, setPreferences] = useState<ChartPreferences>(loadPreferences);

  // Sync with localStorage on mount
  useEffect(() => {
    setPreferences(loadPreferences());
  }, []);

  const updatePreferences = useCallback((updates: Partial<ChartPreferences>) => {
    setPreferences(prev => {
      const next = { ...prev, ...updates };
      savePreferences(next);
      return next;
    });
  }, []);

  const resetPreferences = useCallback(() => {
    setPreferences(DEFAULT_PREFERENCES);
    savePreferences(DEFAULT_PREFERENCES);
  }, []);

  return {
    preferences,
    updatePreferences,
    resetPreferences,
  };
}

/**
 * Hook for managing view mode state with localStorage persistence
 *
 * @param initialMode - Initial view mode (defaults to user preference)
 * @returns Current mode and setter function
 */
export function useViewMode(initialMode?: ViewMode) {
  const { preferences, updatePreferences } = useChartPreferences();
  const [viewMode, setViewMode] = useState<ViewMode>(
    initialMode ?? preferences.defaultViewMode
  );

  const setMode = useCallback((mode: ViewMode) => {
    setViewMode(mode);
  }, []);

  const setAsDefault = useCallback((mode: ViewMode) => {
    updatePreferences({ defaultViewMode: mode });
  }, [updatePreferences]);

  return {
    viewMode,
    setViewMode: setMode,
    setAsDefault,
    isDefault: viewMode === preferences.defaultViewMode,
  };
}
