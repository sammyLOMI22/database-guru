
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';

vi.mock('../src/services/lineageApi', () => ({
    lineageAPI: {
        analyzeImpact: vi.fn(),
    },
}));

import { lineageAPI } from '../src/services/lineageApi';
import { ImpactAnalysisPanel } from '../src/components/lineage/ImpactAnalysisPanel';

const mockImpactResponse = {
    impacted_queries: [
        {
            query_id: 1,
            generated_sql: 'SELECT name FROM customers',
            natural_language_query: 'Show customer names',
            impact_type: 'select',
            risk_level: 'low',
        },
        {
            query_id: 2,
            generated_sql: 'SELECT * FROM customers WHERE status = "active"',
            natural_language_query: 'Active customers',
            impact_type: 'filter',
            risk_level: 'medium',
        },
    ],
    total_affected: 2,
    risk_level: 'medium',
    risk_counts: { low: 0, medium: 2, high: 0 },
    summary: '2 queries impacted',
    changed_object: 'customers.name',
    object_type: 'column'
};

describe('ImpactAnalysisPanel', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    describe('Loading State', () => {
        it('shows loading indicator when analyzing', async () => {
            // Make the mock hang to show loading state
            vi.mocked(lineageAPI.analyzeImpact).mockImplementation(
                () => new Promise(() => {}) // Never resolves
            );

            render(<ImpactAnalysisPanel tableName="customers" autoAnalyze={true} />);

            expect(screen.getByText(/analyzing impact/i)).toBeInTheDocument();
        });

        it('renders nothing without autoAnalyze', () => {
            render(<ImpactAnalysisPanel tableName="customers" />);

            // Without autoAnalyze, no API call, no result, renders null
            expect(screen.queryByText(/analyzing/i)).not.toBeInTheDocument();
            expect(screen.queryByText(/impact/i)).not.toBeInTheDocument();
        });
    });

    describe('Impact Results', () => {
        it('displays impact summary after analysis', async () => {
            vi.mocked(lineageAPI.analyzeImpact).mockResolvedValueOnce(mockImpactResponse);

            render(<ImpactAnalysisPanel tableName="customers" columnName="name" autoAnalyze={true} />);

            await waitFor(() => {
                // Check for summary text
                expect(screen.getByText(/2 queries impacted/i)).toBeInTheDocument();
            });
        });

        it('shows risk level badge', async () => {
            vi.mocked(lineageAPI.analyzeImpact).mockResolvedValueOnce(mockImpactResponse);

            render(<ImpactAnalysisPanel tableName="customers" autoAnalyze={true} />);

            await waitFor(() => {
                // Risk level badge shows "MEDIUM" (uppercase)
                expect(screen.getByText('MEDIUM')).toBeInTheDocument();
            });
        });

        it('displays affected queries when present', async () => {
            vi.mocked(lineageAPI.analyzeImpact).mockResolvedValueOnce(mockImpactResponse);

            render(<ImpactAnalysisPanel tableName="customers" autoAnalyze={true} />);

            await waitFor(() => {
                // Shows affected queries header
                expect(screen.getByText(/Affected Queries \(2\)/i)).toBeInTheDocument();
            });
        });

        it('shows changed object in header', async () => {
            vi.mocked(lineageAPI.analyzeImpact).mockResolvedValueOnce(mockImpactResponse);

            render(<ImpactAnalysisPanel tableName="customers" columnName="name" autoAnalyze={true} />);

            await waitFor(() => {
                expect(screen.getByText(/Impact: customers\.name/i)).toBeInTheDocument();
            });
        });
    });

    describe('Empty Results', () => {
        it('shows summary but no affected queries section when zero impact', async () => {
            vi.mocked(lineageAPI.analyzeImpact).mockResolvedValueOnce({
                impacted_queries: [],
                total_affected: 0,
                risk_level: 'low',
                risk_counts: { low: 0, medium: 0, high: 0 },
                summary: 'No queries would be affected',
                changed_object: 'unused_table',
                object_type: 'table'
            });

            render(<ImpactAnalysisPanel tableName="unused_table" autoAnalyze={true} />);

            await waitFor(() => {
                // Summary should show
                expect(screen.getByText(/No queries would be affected/i)).toBeInTheDocument();
                // LOW risk badge
                expect(screen.getByText('LOW')).toBeInTheDocument();
            });

            // Affected Queries section should NOT be rendered (impacted_queries.length === 0)
            expect(screen.queryByText(/Affected Queries/i)).not.toBeInTheDocument();
        });
    });

    describe('Error Handling', () => {
        it('displays error message on API failure', async () => {
            vi.mocked(lineageAPI.analyzeImpact).mockRejectedValueOnce(new Error('Network error'));

            render(<ImpactAnalysisPanel tableName="customers" autoAnalyze={true} />);

            await waitFor(() => {
                expect(screen.getByText(/Network error/i)).toBeInTheDocument();
            });
        });
    });
});
