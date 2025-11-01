import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ConfidenceBadge } from '../src/components/ConfidenceBadge';
import { ConfidencePrediction } from '../src/types/api';

describe('ConfidenceBadge', () => {
  const mockHighConfidence: ConfidencePrediction = {
    overall: 0.925,
    level: 'HIGH',
    factors: {
      error_type: 0.255,
      schema_match: 0.250,
      historical_success: 0.170,
      correction_complexity: 0.150,
      similarity: 0.100
    },
    reasoning: 'This correction has high confidence (92.5%). Table Not Found errors are relatively easy to fix.',
    recommendation: 'EXECUTE - High confidence, likely to succeed'
  };

  const mockMediumConfidence: ConfidencePrediction = {
    overall: 0.675,
    level: 'MEDIUM',
    factors: {
      error_type: 0.180,
      schema_match: 0.188,
      historical_success: 0.120,
      correction_complexity: 0.127,
      similarity: 0.060
    },
    reasoning: 'This correction has medium confidence (67.5%). Syntax errors have moderate difficulty.',
    recommendation: 'EXECUTE_WITH_CAUTION - Medium confidence, may need fallback'
  };

  const mockLowConfidence: ConfidencePrediction = {
    overall: 0.295,
    level: 'LOW',
    factors: {
      error_type: 0.090,
      schema_match: 0.063,
      historical_success: 0.060,
      correction_complexity: 0.053,
      similarity: 0.029
    },
    reasoning: 'This correction has low confidence (29.5%). Complex rewrites are difficult.',
    recommendation: 'CONSIDER_ALTERNATIVES - Low confidence, try other approaches'
  };

  const mockVeryLowConfidence: ConfidencePrediction = {
    overall: 0.105,
    level: 'VERY_LOW',
    factors: {
      error_type: 0.030,
      schema_match: 0.025,
      historical_success: 0.020,
      correction_complexity: 0.020,
      similarity: 0.010
    },
    reasoning: 'This correction has very low confidence (10.5%). Connection errors cannot be fixed by SQL changes.',
    recommendation: 'SKIP - Very low confidence, avoid execution'
  };

  describe('Badge Display', () => {
    it('renders high confidence badge correctly', () => {
      render(<ConfidenceBadge confidence={mockHighConfidence} />);

      expect(screen.getByText('92.5%')).toBeInTheDocument();
      expect(screen.getByText('HIGH')).toBeInTheDocument();
      expect(screen.getByRole('img', { hidden: true })).toHaveTextContent('🎯');
    });

    it('renders medium confidence badge correctly', () => {
      render(<ConfidenceBadge confidence={mockMediumConfidence} />);

      expect(screen.getByText('67.5%')).toBeInTheDocument();
      expect(screen.getByText('MEDIUM')).toBeInTheDocument();
      expect(screen.getByRole('img', { hidden: true })).toHaveTextContent('⚡');
    });

    it('renders low confidence badge correctly', () => {
      render(<ConfidenceBadge confidence={mockLowConfidence} />);

      expect(screen.getByText('29.5%')).toBeInTheDocument();
      expect(screen.getByText('LOW')).toBeInTheDocument();
      expect(screen.getByRole('img', { hidden: true })).toHaveTextContent('⚠️');
    });

    it('renders very low confidence badge correctly', () => {
      render(<ConfidenceBadge confidence={mockVeryLowConfidence} />);

      expect(screen.getByText('10.5%')).toBeInTheDocument();
      expect(screen.getByText('VERY_LOW')).toBeInTheDocument();
      expect(screen.getByRole('img', { hidden: true })).toHaveTextContent('🚫');
    });
  });

  describe('Color Coding', () => {
    it('applies green styling for high confidence', () => {
      const { container } = render(<ConfidenceBadge confidence={mockHighConfidence} />);
      const badge = container.querySelector('button');

      expect(badge).toHaveClass('bg-green-100');
      expect(badge).toHaveClass('text-green-800');
      expect(badge).toHaveClass('border-green-300');
    });

    it('applies yellow styling for medium confidence', () => {
      const { container } = render(<ConfidenceBadge confidence={mockMediumConfidence} />);
      const badge = container.querySelector('button');

      expect(badge).toHaveClass('bg-yellow-100');
      expect(badge).toHaveClass('text-yellow-800');
      expect(badge).toHaveClass('border-yellow-300');
    });

    it('applies orange styling for low confidence', () => {
      const { container } = render(<ConfidenceBadge confidence={mockLowConfidence} />);
      const badge = container.querySelector('button');

      expect(badge).toHaveClass('bg-orange-100');
      expect(badge).toHaveClass('text-orange-800');
      expect(badge).toHaveClass('border-orange-300');
    });

    it('applies red styling for very low confidence', () => {
      const { container } = render(<ConfidenceBadge confidence={mockVeryLowConfidence} />);
      const badge = container.querySelector('button');

      expect(badge).toHaveClass('bg-red-100');
      expect(badge).toHaveClass('text-red-800');
      expect(badge).toHaveClass('border-red-300');
    });
  });

  describe('Expandable Details', () => {
    it('starts collapsed by default', () => {
      render(<ConfidenceBadge confidence={mockHighConfidence} />);

      // Details should not be visible initially
      expect(screen.queryByText(/Analysis:/)).not.toBeInTheDocument();
      expect(screen.queryByText(/Contributing Factors:/)).not.toBeInTheDocument();
    });

    it('expands when clicked', () => {
      render(<ConfidenceBadge confidence={mockHighConfidence} />);

      const badge = screen.getByRole('button');
      fireEvent.click(badge);

      // Details should now be visible
      expect(screen.getByText(/Analysis:/)).toBeInTheDocument();
      expect(screen.getByText(/Recommendation:/)).toBeInTheDocument();
      expect(screen.getByText(/Contributing Factors:/)).toBeInTheDocument();
    });

    it('displays reasoning when expanded', () => {
      render(<ConfidenceBadge confidence={mockHighConfidence} />);

      fireEvent.click(screen.getByRole('button'));

      expect(screen.getByText(mockHighConfidence.reasoning)).toBeInTheDocument();
    });

    it('displays recommendation when expanded', () => {
      render(<ConfidenceBadge confidence={mockHighConfidence} />);

      fireEvent.click(screen.getByRole('button'));

      expect(screen.getByText(mockHighConfidence.recommendation)).toBeInTheDocument();
    });

    it('displays all factor labels when expanded', () => {
      render(<ConfidenceBadge confidence={mockHighConfidence} />);

      fireEvent.click(screen.getByRole('button'));

      expect(screen.getByText('Error Type Difficulty')).toBeInTheDocument();
      expect(screen.getByText('Schema Match')).toBeInTheDocument();
      expect(screen.getByText('Historical Success')).toBeInTheDocument();
      expect(screen.getByText('Correction Complexity')).toBeInTheDocument();
      expect(screen.getByText('Similarity to Original')).toBeInTheDocument();
    });

    it('displays factor percentages when expanded', () => {
      render(<ConfidenceBadge confidence={mockHighConfidence} />);

      fireEvent.click(screen.getByRole('button'));

      expect(screen.getByText('25.5%')).toBeInTheDocument(); // error_type
      expect(screen.getByText('25.0%')).toBeInTheDocument(); // schema_match
      expect(screen.getByText('17.0%')).toBeInTheDocument(); // historical_success
      expect(screen.getByText('15.0%')).toBeInTheDocument(); // correction_complexity
      expect(screen.getByText('10.0%')).toBeInTheDocument(); // similarity
    });

    it('collapses when clicked again', () => {
      render(<ConfidenceBadge confidence={mockHighConfidence} />);

      const badge = screen.getByRole('button');

      // Expand
      fireEvent.click(badge);
      expect(screen.getByText(/Analysis:/)).toBeInTheDocument();

      // Collapse
      fireEvent.click(badge);
      expect(screen.queryByText(/Analysis:/)).not.toBeInTheDocument();
    });
  });

  describe('showDetails prop', () => {
    it('hides details when showDetails is false', () => {
      render(<ConfidenceBadge confidence={mockHighConfidence} showDetails={false} />);

      const badge = screen.getByRole('button');

      // Badge should be disabled
      expect(badge).toBeDisabled();

      // No chevron icon
      expect(badge.querySelector('svg')).not.toBeInTheDocument();

      // Click should not expand
      fireEvent.click(badge);
      expect(screen.queryByText(/Analysis:/)).not.toBeInTheDocument();
    });

    it('shows details when showDetails is true (default)', () => {
      render(<ConfidenceBadge confidence={mockHighConfidence} />);

      const badge = screen.getByRole('button');

      // Badge should be enabled
      expect(badge).not.toBeDisabled();

      // Chevron icon should be present
      expect(badge.querySelector('svg')).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('has proper aria-label on badge', () => {
      render(<ConfidenceBadge confidence={mockHighConfidence} />);

      const badge = screen.getByLabelText('High Confidence: 92.5%');
      expect(badge).toBeInTheDocument();
    });

    it('has proper aria-expanded state', () => {
      render(<ConfidenceBadge confidence={mockHighConfidence} />);

      const badge = screen.getByRole('button');

      // Initially collapsed
      expect(badge).toHaveAttribute('aria-expanded', 'false');

      // Expanded after click
      fireEvent.click(badge);
      expect(badge).toHaveAttribute('aria-expanded', 'true');
    });

    it('has proper aria attributes on progress bars', () => {
      render(<ConfidenceBadge confidence={mockHighConfidence} />);

      fireEvent.click(screen.getByRole('button'));

      const progressBars = screen.getAllByRole('progressbar');

      // Should have progress bars for each factor + overall
      expect(progressBars.length).toBeGreaterThan(0);

      progressBars.forEach(bar => {
        expect(bar).toHaveAttribute('aria-valuenow');
        expect(bar).toHaveAttribute('aria-valuemin', '0');
        expect(bar).toHaveAttribute('aria-valuemax', '1');
      });
    });
  });

  describe('Edge Cases', () => {
    it('handles 0% confidence correctly', () => {
      const zeroConfidence: ConfidencePrediction = {
        ...mockVeryLowConfidence,
        overall: 0.0,
        factors: {
          error_type: 0,
          schema_match: 0,
          historical_success: 0,
          correction_complexity: 0,
          similarity: 0
        }
      };

      render(<ConfidenceBadge confidence={zeroConfidence} />);

      // Component displays 0% correctly while preventing division by zero in calculations
      expect(screen.getByText('0.0%')).toBeInTheDocument();
    });

    it('handles 100% confidence correctly', () => {
      const perfectConfidence: ConfidencePrediction = {
        ...mockHighConfidence,
        overall: 1.0
      };

      render(<ConfidenceBadge confidence={perfectConfidence} />);

      expect(screen.getByText('100.0%')).toBeInTheDocument();
    });

    it('rounds percentages to 1 decimal place', () => {
      const oddConfidence: ConfidencePrediction = {
        ...mockHighConfidence,
        overall: 0.8734
      };

      render(<ConfidenceBadge confidence={oddConfidence} />);

      expect(screen.getByText('87.3%')).toBeInTheDocument();
    });
  });
});
