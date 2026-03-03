import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { SubmitPage } from './SubmitPage';
import * as api from '../api';
import { MemoryRouter, useNavigate } from 'react-router-dom';

vi.mock('../api');
vi.mock('react-router-dom', async (importOriginal) => {
    const actual = await importOriginal<typeof import('react-router-dom')>();
    return {
        ...actual,
        useNavigate: vi.fn(),
    };
});

describe('SubmitPage', () => {
    const mockNavigate = vi.fn();

    beforeEach(() => {
        vi.clearAllMocks();
        vi.mocked(useNavigate).mockReturnValue(mockNavigate);
    });

    it('renders textarea with example payload', () => {
        render(<SubmitPage />);
        const textarea = screen.getByRole('textbox') as HTMLTextAreaElement;
        expect(textarea).toBeInTheDocument();
        expect(textarea.value).toContain('"name": "AI Data Pipeline"');
        expect(textarea.value).toContain('"action": "fetch_dataset"');
    });

    it('shows error on invalid JSON', async () => {
        render(<SubmitPage />);
        const textarea = screen.getByRole('textbox');
        const submitBtn = screen.getByRole('button', { name: /Submit Pipeline/i });

        fireEvent.change(textarea, { target: { value: '{"broken": json' } });
        fireEvent.click(submitBtn);

        const error = await screen.findByRole('alert');
        expect(error).toHaveTextContent(/Invalid JSON/i);
        expect(api.submitWorkflow).not.toHaveBeenCalled();
    });

    it('calls submitWorkflow and navigates on valid payload', async () => {
        vi.mocked(api.submitWorkflow).mockResolvedValueOnce({ workflow_id: '123' });

        render(<SubmitPage />);
        const submitBtn = screen.getByRole('button', { name: /Submit Pipeline/i });

        fireEvent.click(submitBtn);

        await waitFor(() => {
            expect(api.submitWorkflow).toHaveBeenCalled();
        });

        expect(mockNavigate).toHaveBeenCalledWith('/runs/123');
    });

    it('shows API error in banner on failure', async () => {
        vi.mocked(api.submitWorkflow).mockRejectedValueOnce(new Error('Backend validation failed'));

        render(<SubmitPage />);
        const submitBtn = screen.getByRole('button', { name: /Submit Pipeline/i });

        fireEvent.click(submitBtn);

        const error = await screen.findByRole('alert');
        expect(error).toHaveTextContent('Backend validation failed');
        expect(mockNavigate).not.toHaveBeenCalled();
    });

    it('handles non-Error objects thrown by api client', async () => {
        vi.mocked(api.submitWorkflow).mockRejectedValueOnce('Some string error');
        render(
            <MemoryRouter>
                <SubmitPage />
            </MemoryRouter>
        );

        const btn = screen.getByRole('button', { name: /Submit Pipeline/i });
        await act(async () => {
            fireEvent.click(btn);
        });

        expect(screen.getByText('Submission failed')).toBeInTheDocument();
    });
});
