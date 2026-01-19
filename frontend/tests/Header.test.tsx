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
      render(<Header isHealthy={true} isDarkMode={false} toggleDarkMode={() => {}} activeTab="chat" onTabChange={() => {}} />);

      expect(screen.getByText('Database Guru')).toBeInTheDocument();
    });

    it('displays the subtitle', () => {
      render(<Header isHealthy={true} isDarkMode={false} toggleDarkMode={() => {}} activeTab="chat" onTabChange={() => {}} />);

      expect(screen.getByText('AI SQL Assistant')).toBeInTheDocument();
    });

    it('displays the wizard emoji', () => {
      render(<Header isHealthy={true} isDarkMode={false} toggleDarkMode={() => {}} activeTab="chat" onTabChange={() => {}} />);

      expect(screen.getByText('🧙‍♂️')).toBeInTheDocument();
    });
  });

  describe('Health Status', () => {
    it('shows connected status when healthy', () => {
      render(<Header isHealthy={true} isDarkMode={false} toggleDarkMode={() => {}} activeTab="chat" onTabChange={() => {}} />);

      expect(screen.getByText('Online')).toBeInTheDocument();
    });

    it('shows disconnected status when unhealthy', () => {
      render(<Header isHealthy={false} isDarkMode={false} toggleDarkMode={() => {}} activeTab="chat" onTabChange={() => {}} />);

      expect(screen.getByText('Offline')).toBeInTheDocument();
    });

    it('displays green indicator when healthy', () => {
      const { container } = render(<Header isHealthy={true} isDarkMode={false} toggleDarkMode={() => {}} activeTab="chat" onTabChange={() => {}} />);

      const indicator = container.querySelector('.bg-green-500');
      expect(indicator).toBeInTheDocument();
    });

    it('displays no green indicator when unhealthy', () => {
      const { container } = render(<Header isHealthy={false} isDarkMode={false} toggleDarkMode={() => {}} activeTab="chat" onTabChange={() => {}} />);

      // When unhealthy, there's no green ping indicator
      const indicator = container.querySelector('.bg-green-500.animate-ping');
      expect(indicator).not.toBeInTheDocument();
    });
  });

  describe('GitHub Link', () => {
    it('renders GitHub link with correct attributes', () => {
      render(<Header isHealthy={true} isDarkMode={false} toggleDarkMode={() => {}} activeTab="chat" onTabChange={() => {}} />);

      const link = screen.getByRole('link');
      expect(link).toBeInTheDocument();
      expect(link).toHaveAttribute('href', 'https://github.com/sammyLOMI22/database-guru');
      expect(link).toHaveAttribute('target', '_blank');
      expect(link).toHaveAttribute('rel', 'noopener noreferrer');
    });

    it('renders GitHub icon SVG', () => {
      const { container } = render(<Header isHealthy={true} isDarkMode={false} toggleDarkMode={() => {}} activeTab="chat" onTabChange={() => {}} />);

      // There are multiple SVGs (lucide icons), find the GitHub one in the link
      const link = container.querySelector('a[href*="github"]');
      expect(link).toBeInTheDocument();
      const svg = link?.querySelector('svg');
      expect(svg).toBeInTheDocument();
      // GitHub icon uses fill="currentColor" with path-based rendering
      expect(svg).toHaveAttribute('fill', 'currentColor');
    });
  });
});
