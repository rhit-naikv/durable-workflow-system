import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { DashboardPage } from './DashboardPage';
import { listWorkflows } from '../api';
import { useNavigate } from 'react-router-dom';

vi.mock('../api');
vi.mock('react-router-dom', () => ({
    useNavigate: vi.fn(),
}));

describe('DashboardPage', () => {
    const mockNavigate = vi.fn();

    beforeEach(() => {
        vi.clearAllMocks();
        vi.mocked(useNavigate).mockReturnValue(mockNavigate);
    });

    it('shows loading state initially', () => {
        vi.mocked(listWorkflows).mockReturnValue(new Promise(() => { }));
        render(<DashboardPage />);
        expect(screen.getByText('Loading runs…')).toBeInTheDocument();
    });

    it('shows empty state when no workflows exist', async () => {
        vi.mocked(listWorkflows).mockResolvedValueOnce([]);
        render(<DashboardPage />);

        await waitFor(() => {
            expect(screen.getByText('No pipeline runs yet')).toBeInTheDocument();
        });
    });

    it('renders workflows list correctly', async () => {
        const mockWorkflows = [
            {
                workflow_id: 'uuid-1',
                name: 'Flow 1',
                status: 'COMPLETED' as const,
                created_at: '2025-01-01T12:00:00Z',
                completed_at: '2025-01-01T12:00:05Z',
                total_steps: 3,
                completed_steps: 3,
            },
            {
                workflow_id: 'uuid-2',
                name: 'Flow 2',
                status: 'RUNNING' as const,
                created_at: '2025-01-01T12:05:00Z',
                completed_at: null,
                total_steps: 5,
                completed_steps: 2,
            },
        ];
        vi.mocked(listWorkflows).mockResolvedValue(mockWorkflows);

        render(<DashboardPage />);

        await waitFor(() => {
            expect(screen.getByText('Flow 1')).toBeInTheDocument();
        });

        expect(screen.getByText('Flow 2')).toBeInTheDocument();
        expect(screen.getByText('uuid-1…')).toBeInTheDocument();

        // Duration calculations
        expect(screen.getByText('5.0s')).toBeInTheDocument(); // Flow 1 completed
        expect(screen.getAllByText('—').length).toBeGreaterThan(0); // Flow 2 not completed
    });

    it('shows error banner on API failure', async () => {
        vi.mocked(listWorkflows).mockRejectedValueOnce(new Error('Failed to load'));
        render(<DashboardPage />);

        await waitFor(() => {
            expect(screen.getByRole('alert')).toHaveTextContent('Failed to load');
        });
    });

    it('polls for data every 5 seconds', async () => {
        vi.useFakeTimers();
        vi.mocked(listWorkflows).mockResolvedValue([]);
        render(<DashboardPage />);

        // Initial fetch
        expect(listWorkflows).toHaveBeenCalledTimes(1);

        // Fast forward 5 seconds
        await vi.advanceTimersByTimeAsync(5001);
        expect(listWorkflows).toHaveBeenCalledTimes(2);

        // Fast forward another 5 seconds
        await vi.advanceTimersByTimeAsync(5000);
        expect(listWorkflows).toHaveBeenCalledTimes(3);
        vi.useRealTimers();
    });

    it('navigates to run detail when row is clicked', async () => {
        const mockWorkflows = [
            {
                workflow_id: 'uuid-1',
                name: 'Flow 1',
                status: 'COMPLETED' as const,
                created_at: '2025-01-01T12:00:00Z',
                completed_at: '2025-01-01T12:00:05Z',
                total_steps: 3,
                completed_steps: 3,
            }
        ];
        vi.mocked(listWorkflows).mockResolvedValue(mockWorkflows);

        render(<DashboardPage />);

        await waitFor(() => {
            expect(screen.getByText('Flow 1')).toBeInTheDocument();
        });

        // Click the row (which contains the text "Flow 1")
        screen.getByText('Flow 1').click();
        expect(mockNavigate).toHaveBeenCalledWith('/runs/uuid-1');
    });
});
