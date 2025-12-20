/**
 * Header Component Tests
 *
 * Tests the application header with health status
 */

import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import Header from '../src/components/Header';

describe('Header', () => {
  describe('Branding', () => {
    it('displays the application title', () => {
      render(<Header isHealthy={true} />);

      expect(screen.getByText('Database Guru')).toBeInTheDocument();
    });

    it('displays the subtitle', () => {
      render(<Header isHealthy={true} />);

      expect(screen.getByText('AI-Powered SQL Assistant')).toBeInTheDocument();
    });

    it('displays the wizard emoji', () => {
      render(<Header isHealthy={true} />);

      expect(screen.getByText('🧙‍♂️')).toBeInTheDocument();
    });
  });

  describe('Health Status', () => {
    it('shows connected status when healthy', () => {
      render(<Header isHealthy={true} />);

      expect(screen.getByText('Connected')).toBeInTheDocument();
    });

    it('shows disconnected status when unhealthy', () => {
      render(<Header isHealthy={false} />);

      expect(screen.getByText('Disconnected')).toBeInTheDocument();
    });

    it('displays green indicator when healthy', () => {
      const { container } = render(<Header isHealthy={true} />);

      const indicator = container.querySelector('.bg-green-500');
      expect(indicator).toBeInTheDocument();
    });

    it('displays red indicator when unhealthy', () => {
      const { container } = render(<Header isHealthy={false} />);

      const indicator = container.querySelector('.bg-red-500');
      expect(indicator).toBeInTheDocument();
    });
  });

  describe('GitHub Link', () => {
    it('renders GitHub link with correct attributes', () => {
      render(<Header isHealthy={true} />);

      const link = screen.getByRole('link');
      expect(link).toBeInTheDocument();
      expect(link).toHaveAttribute('href', 'https://github.com/yourusername/database-guru');
      expect(link).toHaveAttribute('target', '_blank');
      expect(link).toHaveAttribute('rel', 'noopener noreferrer');
    });

    it('renders GitHub icon SVG', () => {
      const { container } = render(<Header isHealthy={true} />);

      const svg = container.querySelector('svg');
      expect(svg).toBeInTheDocument();
      // Lucide icons use fill="none" with stroke-based rendering
      expect(svg).toHaveAttribute('fill', 'none');
      expect(svg).toHaveAttribute('viewBox', '0 0 24 24');
    });
  });
});
