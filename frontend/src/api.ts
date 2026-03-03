/**
 * API client for the Durable Workflow Engine backend.
 */

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// ── Types ─────────────────────────────────────────────────────────────────────

export type StepStatus = 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED';
export type WorkflowStatus = 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED';

export interface StepConfig {
    action: string;
    params?: Record<string, unknown>;
}

export interface WorkflowStep {
    id: string;
    name?: string;
    type?: string;
    config: StepConfig;
    depends_on: string[];
}

export interface WorkflowDefinition {
    name: string;
    steps: WorkflowStep[];
}

export interface WorkflowRunResponse {
    workflow_id: string;
}

export interface StepStatusResponse {
    step_id: string;
    step_name: string;
    status: StepStatus;
    action: string;
    depends_on: string[];
    result_payload: Record<string, unknown> | null;
    started_at: string | null;
    completed_at: string | null;
}

export interface WorkflowStateResponse {
    workflow_id: string;
    name: string;
    status: WorkflowStatus;
    created_at: string;
    completed_at: string | null;
    steps: StepStatusResponse[];
}

export interface WorkflowSummaryResponse {
    workflow_id: string;
    name: string;
    status: WorkflowStatus;
    created_at: string;
    completed_at: string | null;
    total_steps: number;
    completed_steps: number;
}

// ── API Functions ─────────────────────────────────────────────────────────────

/**
 * Extract a human-readable error message from a FastAPI/Pydantic error response.
 * Handles both simple string `detail` (HTTPException) and array `detail` (Pydantic 422).
 */
function extractErrorMessage(body: Record<string, unknown>, status: number): string {
    const detail = body.detail;

    // Pydantic validation errors: detail is an array of { msg, loc, type, ... }
    if (Array.isArray(detail) && detail.length > 0) {
        return detail
            .map((err: Record<string, unknown>) => {
                const msg = String(err.msg ?? 'Validation error');
                // Strip Pydantic's "Value error, " prefix for cleaner display
                return msg.replace(/^Value error,\s*/i, '');
            })
            .join('; ');
    }

    // Simple HTTPException: detail is a string
    if (typeof detail === 'string') return detail;

    return `HTTP ${status}`;
}

export async function submitWorkflow(definition: WorkflowDefinition): Promise<WorkflowRunResponse> {
    const res = await fetch(`${API_BASE}/api/workflows`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(definition),
    });
    if (!res.ok) {
        const body = await res.json().catch(() => ({ detail: 'Unknown error' }));
        throw new Error(extractErrorMessage(body, res.status));
    }
    return res.json();
}

export async function listWorkflows(): Promise<WorkflowSummaryResponse[]> {
    const res = await fetch(`${API_BASE}/api/workflows`);
    if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(extractErrorMessage(body, res.status));
    }
    return res.json();
}

export async function getWorkflowState(workflowId: string): Promise<WorkflowStateResponse> {
    const res = await fetch(`${API_BASE}/api/workflows/${workflowId}/state`);
    if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(extractErrorMessage(body, res.status));
    }
    return res.json();
}
