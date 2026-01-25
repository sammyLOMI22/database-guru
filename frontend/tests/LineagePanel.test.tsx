
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock child components - must match actual export types
vi.mock('../src/components/lineage/LineageGraph', () => ({
    default: () => <div data-testid="lineage-graph">LineageGraph</div>,
}));

vi.mock('../src/components/lineage/ColumnLineage', () => ({
    ColumnLineage: () => <div data-testid="column-lineage">ColumnLineage</div>,
}));

vi.mock('../src/components/lineage/ImpactAnalysisPanel', () => ({
    ImpactAnalysisPanel: () => <div data-testid="impact-panel">ImpactAnalysisPanel</div>,
}));

vi.mock('../src/components/lineage/QueryPatternHeatmap', () => ({
    QueryPatternHeatmap: () => <div data-testid="heatmap">QueryPatternHeatmap</div>,
}));

// Mock services
vi.mock('../src/services/lineageApi', () => ({
    lineageAPI: {
        // Mock any calls LineagePanel makes directly (e.g. initial stats?)
    }
}));

import { LineagePanel } from '../src/components/lineage/LineagePanel';

describe('LineagePanel', () => {

    describe('Tab Navigation', () => {
        it('renders with Explore tab active by default', () => {
            render(<LineagePanel />);

            // Using text because buttons render icon + text
            expect(screen.getByText(/Explore/i).closest('button')).toHaveClass('bg-indigo-600');
            expect(screen.getByTestId('lineage-graph')).toBeInTheDocument();
        });

        it('switches to History tab on click', async () => {
            render(<LineagePanel />);

            const historyButton = screen.getByText('History').closest('button');
            fireEvent.click(historyButton!);

            await waitFor(() => {
                expect(historyButton).toHaveClass('bg-indigo-600');
            });
        });

        it('switches to Impact tab on click', async () => {
            render(<LineagePanel />);

            // Find the Impact button by its text and click the button element
            const impactButton = screen.getByText('Impact').closest('button');
            fireEvent.click(impactButton!);

            await waitFor(() => {
                expect(impactButton).toHaveClass('bg-indigo-600');
                // Impact tab shows form inputs, not panel (panel shows after form submit)
                expect(screen.getByTestId('impact-table-input')).toBeInTheDocument();
                expect(screen.getByTestId('impact-analyze-button')).toBeInTheDocument();
            });
        });

        it('switches to Patterns tab on click', async () => {
            render(<LineagePanel />);

            const patternsButton = screen.getByText(/Patterns/i).closest('button');
            fireEvent.click(patternsButton!);

            await waitFor(() => {
                expect(patternsButton).toHaveClass('bg-indigo-600');
                expect(screen.getByTestId('heatmap')).toBeInTheDocument();
            });
        });
    });

    describe('Initialization', () => {
        it('renders correctly without props', () => {
            render(<LineagePanel />);
            // Verify component mounts without error
            expect(screen.getByRole('tablist')).toBeInTheDocument();
        });

        it('can be initialized with a specific tab', () => {
            render(<LineagePanel initialTab="impact" />);

            const impactButton = screen.getByText('Impact').closest('button');
            expect(impactButton).toHaveClass('bg-indigo-600');
        });

        it('can be initialized with impact table', () => {
            render(<LineagePanel initialImpactTable="customers" initialTab="impact" />);

            expect(screen.getByTestId('impact-panel')).toBeInTheDocument();
        });
    });
});
