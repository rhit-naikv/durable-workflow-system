import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { StatusBadge } from './StatusBadge';

describe('StatusBadge', () => {
    it('renders PENDING status correctly', () => {
        render(<StatusBadge status="PENDING" />);
        const badge = screen.getByText(/Pending/i);
        expect(badge).toBeInTheDocument();
        expect(badge).toHaveTextContent('○');
        expect(badge).toHaveClass('badge--pending');
    });

    it('renders RUNNING status correctly', () => {
        render(<StatusBadge status="RUNNING" />);
        const badge = screen.getByText(/Running/i);
        expect(badge).toBeInTheDocument();
        expect(badge).toHaveTextContent('◉');
        expect(badge).toHaveClass('badge--running');
    });

    it('renders COMPLETED status correctly', () => {
        render(<StatusBadge status="COMPLETED" />);
        const badge = screen.getByText(/Completed/i);
        expect(badge).toBeInTheDocument();
        expect(badge).toHaveTextContent('✓');
        expect(badge).toHaveClass('badge--completed');
    });

    it('renders FAILED status correctly', () => {
        render(<StatusBadge status="FAILED" />);
        const badge = screen.getByText(/Failed/i);
        expect(badge).toBeInTheDocument();
        expect(badge).toHaveTextContent('✕');
        expect(badge).toHaveClass('badge--failed');
    });

    it('applies sm size class when size is sm', () => {
        render(<StatusBadge status="PENDING" size="sm" />);
        // get the parent span that carries the badge classes
        const badge = screen.getByText(/Pending/i).closest('span');
        expect(badge).toHaveClass('badge--sm');
    });

    it('does not apply sm size class by default', () => {
        render(<StatusBadge status="PENDING" />);
        const badge = screen.getByText(/Pending/i).closest('span');
        expect(badge).not.toHaveClass('badge--sm');
    });
});
