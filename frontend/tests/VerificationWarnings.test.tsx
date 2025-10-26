/**
 * VerificationWarnings Component Tests
 *
 * Tests the verification warnings display component
 */

import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { VerificationWarnings } from '../src/components/VerificationWarnings';

describe('VerificationWarnings', () => {
  describe('Rendering', () => {
    it('renders warning header', () => {
      const warnings = ['Test warning'];
      render(<VerificationWarnings warnings={warnings} />);

      expect(screen.getByText('Result Verification Warnings')).toBeInTheDocument();
    });

    it('renders warning emoji', () => {
      const warnings = ['Test warning'];
      render(<VerificationWarnings warnings={warnings} />);

      expect(screen.getByText('⚠️')).toBeInTheDocument();
    });

    it('renders help text', () => {
      const warnings = ['Test warning'];
      render(<VerificationWarnings warnings={warnings} />);

      expect(screen.getByText(/These warnings indicate potential issues/)).toBeInTheDocument();
      expect(screen.getByText(/Please review the results carefully/)).toBeInTheDocument();
    });
  });

  describe('Warning Messages', () => {
    it('renders a single warning', () => {
      const warnings = ['Column count mismatch'];
      render(<VerificationWarnings warnings={warnings} />);

      expect(screen.getByText('Column count mismatch')).toBeInTheDocument();
    });

    it('renders multiple warnings', () => {
      const warnings = [
        'Column count mismatch',
        'Unexpected null values detected',
        'Row count differs from expected'
      ];
      render(<VerificationWarnings warnings={warnings} />);

      expect(screen.getByText('Column count mismatch')).toBeInTheDocument();
      expect(screen.getByText('Unexpected null values detected')).toBeInTheDocument();
      expect(screen.getByText('Row count differs from expected')).toBeInTheDocument();
    });

    it('renders each warning in its own container', () => {
      const warnings = ['Warning 1', 'Warning 2', 'Warning 3'];
      const { container } = render(<VerificationWarnings warnings={warnings} />);

      const warningContainers = container.querySelectorAll('.bg-yellow-100.border.border-yellow-300');
      expect(warningContainers.length).toBe(3);
    });
  });

  describe('Empty States', () => {
    it('renders nothing when warnings array is empty', () => {
      const { container } = render(<VerificationWarnings warnings={[]} />);

      expect(container.firstChild).toBeNull();
    });

    it('renders nothing when warnings is null', () => {
      const { container } = render(<VerificationWarnings warnings={null as any} />);

      expect(container.firstChild).toBeNull();
    });

    it('renders nothing when warnings is undefined', () => {
      const { container } = render(<VerificationWarnings warnings={undefined as any} />);

      expect(container.firstChild).toBeNull();
    });
  });

  describe('Styling', () => {
    it('applies correct container styling', () => {
      const warnings = ['Test'];
      const { container } = render(<VerificationWarnings warnings={warnings} />);

      const mainContainer = container.querySelector('.bg-yellow-50.border.border-yellow-200');
      expect(mainContainer).toBeInTheDocument();
    });

    it('applies correct heading styling', () => {
      const warnings = ['Test'];
      render(<VerificationWarnings warnings={warnings} />);

      const heading = screen.getByText('Result Verification Warnings');
      expect(heading.tagName).toBe('H3');
      expect(heading).toHaveClass('font-semibold', 'text-yellow-900');
    });

    it('applies correct warning text styling', () => {
      const warnings = ['Test warning'];
      const { container } = render(<VerificationWarnings warnings={warnings} />);

      const warningText = container.querySelector('.text-sm.text-yellow-900');
      expect(warningText).toBeInTheDocument();
      expect(warningText).toHaveTextContent('Test warning');
    });
  });

  describe('Accessibility', () => {
    it('has proper ARIA label on warning emoji', () => {
      const warnings = ['Test'];
      render(<VerificationWarnings warnings={warnings} />);

      const emoji = screen.getByRole('img', { name: 'Warning' });
      expect(emoji).toBeInTheDocument();
    });

    it('renders warnings in a semantically correct structure', () => {
      const warnings = ['Warning 1', 'Warning 2'];
      const { container } = render(<VerificationWarnings warnings={warnings} />);

      // Check for proper heading structure
      const heading = container.querySelector('h3');
      expect(heading).toBeInTheDocument();

      // Check for proper spacing container
      const warningsContainer = container.querySelector('.space-y-2');
      expect(warningsContainer).toBeInTheDocument();
    });
  });
});
