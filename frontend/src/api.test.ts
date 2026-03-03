import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { submitWorkflow, listWorkflows, getWorkflowState } from './api';

describe('API Client', () => {
    beforeEach(() => {
        vi.stubGlobal('fetch', vi.fn());
    });

    afterEach(() => {
        vi.restoreAllMocks();
    });

    describe('submitWorkflow', () => {
        it('resolves with workflow_id on success', async () => {
            const mockResponse = { workflow_id: 'test-123' };
            vi.mocked(fetch).mockResolvedValueOnce({
                ok: true,
                json: async () => mockResponse,
            } as Response);

            const result = await submitWorkflow({ name: 'Test', steps: [] });
            expect(result).toEqual(mockResponse);
        });

        it('rejects with Pydantic array detail message on 422 error', async () => {
            const mockError = {
                detail: [
                    { msg: 'Value error, Missing field X' },
                    { msg: 'Value error, invalid cycle' },
                ],
            };
            vi.mocked(fetch).mockResolvedValueOnce({
                ok: false,
                status: 422,
                json: async () => mockError,
            } as Response);

            await expect(submitWorkflow({ name: 'Test', steps: [] })).rejects.toThrow(
                'Missing field X; invalid cycle'
            );
        });

        it('rejects with simple string detail error', async () => {
            vi.mocked(fetch).mockResolvedValueOnce({
                ok: false,
                status: 400,
                json: async () => ({ detail: 'Bad request message' }),
            } as Response);

            await expect(submitWorkflow({ name: 'Test', steps: [] })).rejects.toThrow('Bad request message');
        });

        it('rejects with HTTP status if payload unrecognized', async () => {
            vi.mocked(fetch).mockResolvedValueOnce({
                ok: false,
                status: 500,
                json: async () => ({ something_else: true }),
            } as Response);

            await expect(submitWorkflow({ name: 'Test', steps: [] })).rejects.toThrow('HTTP 500');
        });
    });

    describe('listWorkflows', () => {
        it('resolves with array on success', async () => {
            const mockData = [{ workflow_id: '1' }];
            vi.mocked(fetch).mockResolvedValueOnce({
                ok: true,
                json: async () => mockData,
            } as Response);

            const result = await listWorkflows();
            expect(result).toEqual(mockData);
        });

        it('rejects on HTTP error', async () => {
            vi.mocked(fetch).mockResolvedValueOnce({
                ok: false,
                status: 503,
                json: async () => ({}),
            } as Response);

            await expect(listWorkflows()).rejects.toThrow('HTTP 503');
        });
    });

    describe('getWorkflowState', () => {
        it('resolves with state object on success', async () => {
            const mockData = { workflow_id: '1', status: 'PENDING' };
            vi.mocked(fetch).mockResolvedValueOnce({
                ok: true,
                json: async () => mockData,
            } as Response);

            const result = await getWorkflowState('1');
            expect(result).toEqual(mockData);
        });

        it('rejects with detail on 404', async () => {
            vi.mocked(fetch).mockResolvedValueOnce({
                ok: false,
                status: 404,
                json: async () => ({ detail: 'Workflow not found' }),
            } as Response);

            await expect(getWorkflowState('999')).rejects.toThrow('Workflow not found');
        });
    });

    it('extractErrorMessage handles Pydantic error missing msg', async () => {
        vi.mocked(fetch).mockResolvedValueOnce({
            ok: false,
            status: 422,
            json: async () => ({
                detail: [{ loc: ['body', 'name'], type: 'missing' }],
            }),
        } as Response);

        const promise = submitWorkflow({ name: '', steps: [] });
        await expect(promise).rejects.toThrow('Validation error');
    });
});
