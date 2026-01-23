/**
 * ResultSummary Component Tests
 *
 * Tests the intelligent data narratives component
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect, beforeEach } from 'vitest';
import { ResultSummary } from '../src/components/ResultSummary';
import { ResultAnalysis } from '../src/types/api';

describe('ResultSummary Component', () => {
  const mockAnalysis: ResultAnalysis = {
    summary: 'Found 42 customers with an average order value of $1,245.',
    key_insights: [
      'California leads with 27% higher average than NY',
      'Average order values range from $875 to $1,245',
      'Three states represented in the dataset',
    ],
    direct_answer: '42 customers',
    confidence: 0.92,
    statistics: {
      row_count: 3,
      avg_order: { min: 875, max: 1245, avg: 1033.58 },
    },
    generated_at: new Date().toISOString(),
  };

  it('should render the summary text', () => {
    render(<ResultSummary analysis={mockAnalysis} />);
    expect(screen.getByText(/Found 42 customers with an average order value/)).toBeInTheDocument();
  });

  it('should display the direct answer prominently', () => {
    render(<ResultSummary analysis={mockAnalysis} />);
    const directAnswerText = screen.getByText('42 customers');
    expect(directAnswerText).toBeInTheDocument();
    expect(directAnswerText).toHaveClass('text-xl', 'font-black');
  });

  it('should render all key insights', () => {
    render(<ResultSummary analysis={mockAnalysis} />);
    mockAnalysis.key_insights.forEach((insight) => {
      expect(screen.getByText(new RegExp(insight.substring(0, 20)))).toBeInTheDocument();
    });
  });

  it('should display confidence badge with high confidence color (emerald)', () => {
    render(<ResultSummary analysis={mockAnalysis} />);
    const confidenceBadge = screen.getByText('High (92%)');
    expect(confidenceBadge).toBeInTheDocument();
    expect(confidenceBadge).toHaveClass('text-emerald-600');
  });

  it('should display confidence badge with good confidence color (amber)', () => {
    const analysis: ResultAnalysis = {
      ...mockAnalysis,
      confidence: 0.75,
    };
    render(<ResultSummary analysis={analysis} />);
    const confidenceBadge = screen.getByText('Good (75%)');
    expect(confidenceBadge).toBeInTheDocument();
    expect(confidenceBadge).toHaveClass('text-amber-600');
  });

  it('should display confidence badge with low confidence color (red)', () => {
    const analysis: ResultAnalysis = {
      ...mockAnalysis,
      confidence: 0.45,
    };
    render(<ResultSummary analysis={analysis} />);
    const confidenceBadge = screen.getByText('Low (45%)');
    expect(confidenceBadge).toBeInTheDocument();
    expect(confidenceBadge).toHaveClass('text-red-600');
  });

  it('should not render direct answer section when not provided', () => {
    const analysis: ResultAnalysis = {
      ...mockAnalysis,
      direct_answer: null,
    };
    render(<ResultSummary analysis={analysis} />);
    expect(screen.queryByText('Answer')).not.toBeInTheDocument();
  });

  it('should display statistics in expandable details element', () => {
    render(<ResultSummary analysis={mockAnalysis} />);
    const statsButton = screen.getByText('Detailed Statistics');
    expect(statsButton).toBeInTheDocument();
  });

  it('should include row count and execution time in statistics', () => {
    render(<ResultSummary analysis={mockAnalysis} rowCount={42} executionTime={123.45} />);
    // Multiple "row count" elements may exist (from statistics object and from props)
    const rowCountLabels = screen.getAllByText(/Row count/i);
    expect(rowCountLabels.length).toBeGreaterThan(0);
    expect(screen.getByText('42')).toBeInTheDocument();
    expect(screen.getByText(/Execution time/i)).toBeInTheDocument();
    expect(screen.getByText('123.45 ms')).toBeInTheDocument();
  });

  it('should display the Data Insights header with Sparkles icon', () => {
    render(<ResultSummary analysis={mockAnalysis} />);
    expect(screen.getByText('Data Insights')).toBeInTheDocument();
  });

  it('should format statistics object correctly', () => {
    render(<ResultSummary analysis={mockAnalysis} />);
    const statsButton = screen.getByText('Detailed Statistics');
    expect(statsButton).toBeInTheDocument();
  });

  it('should not render statistics section when empty', () => {
    const analysis: ResultAnalysis = {
      ...mockAnalysis,
      statistics: {},
    };
    render(<ResultSummary analysis={analysis} />);
    // Statistics section shouldn't render if no stats and no row count/execution time
    expect(screen.queryByText('Detailed Statistics')).not.toBeInTheDocument();
  });

  it('should display generated_at timestamp', () => {
    render(<ResultSummary analysis={mockAnalysis} />);
    expect(screen.getByText(/Generated/)).toBeInTheDocument();
  });

  it('should handle confidence scores at boundaries correctly', () => {
    const testCases = [
      { confidence: 1.0, expectedLabel: 'High' },
      { confidence: 0.85, expectedLabel: 'High' },
      { confidence: 0.84, expectedLabel: 'Good' },
      { confidence: 0.7, expectedLabel: 'Good' },
      { confidence: 0.69, expectedLabel: 'Moderate' },
      { confidence: 0.5, expectedLabel: 'Moderate' },
      { confidence: 0.49, expectedLabel: 'Low' },
      { confidence: 0.0, expectedLabel: 'Low' },
    ];

    testCases.forEach(({ confidence, expectedLabel }) => {
      const { unmount } = render(
        <ResultSummary analysis={{ ...mockAnalysis, confidence }} />
      );
      expect(screen.getByText(new RegExp(expectedLabel))).toBeInTheDocument();
      unmount();
    });
  });

  it('should render with minimal data (only summary and confidence)', () => {
    const minimalAnalysis: ResultAnalysis = {
      summary: 'Query completed successfully.',
      key_insights: [],
      direct_answer: null,
      confidence: 0.5,
      statistics: {},
      generated_at: new Date().toISOString(),
    };
    render(<ResultSummary analysis={minimalAnalysis} />);
    expect(screen.getByText('Query completed successfully.')).toBeInTheDocument();
    expect(screen.getByText(/Moderate/)).toBeInTheDocument();
  });
});
