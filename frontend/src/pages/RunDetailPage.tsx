import { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getWorkflowState, type WorkflowStateResponse, type StepStatusResponse } from '../api';
import { StatusBadge } from '../components/StatusBadge';

/** Kahn's algorithm — returns steps in topological (dependency) order. */
function topoSort(steps: StepStatusResponse[]): StepStatusResponse[] {
    const stepMap = new Map(steps.map((s) => [s.step_id, s]));
    const inDegree = new Map(steps.map((s) => [s.step_id, s.depends_on.length]));
    const dependents = new Map<string, string[]>(steps.map((s) => [s.step_id, []]));

    for (const step of steps) {
        for (const dep of step.depends_on) {
            dependents.get(dep)?.push(step.step_id);
        }
    }

    const queue = steps.filter((s) => s.depends_on.length === 0).map((s) => s.step_id);
    const sorted: StepStatusResponse[] = [];

    while (queue.length > 0) {
        const id = queue.shift()!;
        sorted.push(stepMap.get(id)!);
        for (const dep of dependents.get(id) ?? []) {
            const deg = (inDegree.get(dep) ?? 1) - 1;
            inDegree.set(dep, deg);
            if (deg === 0) queue.push(dep);
        }
    }

    // Append any remaining steps (e.g. cycles) so nothing is lost
    if (sorted.length < steps.length) {
        const seen = new Set(sorted.map((s) => s.step_id));
        for (const s of steps) if (!seen.has(s.step_id)) sorted.push(s);
    }

    return sorted;
}

function formatDuration(start: string | null, end: string | null): string {
    if (!start) return '—';
    const s = new Date(start).getTime();
    const e = end ? new Date(end).getTime() : Date.now();
    const ms = e - s;
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(1)}s`;
}

function formatTimestamp(iso: string | null): string {
    if (!iso) return '—';
    return new Date(iso).toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
    });
}

const ACTION_ICONS: Record<string, string> = {
    validate_order: '📋',
    fetch_dataset: '📥',
    generate_prompt: '✏️',
    call_llm: '🤖',
    validate_output: '✅',
    store_results: '💾',
};

function StepCard({ step, index }: { step: StepStatusResponse; index: number }) {
    const [expanded, setExpanded] = useState(false);
    const icon = ACTION_ICONS[step.action] || '⚙️';

    return (
        <div
            className={`step-card step-card--${step.status.toLowerCase()}`}
            style={{ animationDelay: `${index * 80}ms` }}
        >
            <div className="step-card__connector" />
            <div
                className="step-card__content"
                onClick={() => step.result_payload && setExpanded(!expanded)}
                role={step.result_payload ? 'button' : undefined}
                tabIndex={step.result_payload ? 0 : undefined}
            >
                <div className="step-card__header">
                    <div className="step-card__left">
                        <span className="step-card__icon">{icon}</span>
                        <div>
                            <h3 className="step-card__name">{step.step_name}</h3>
                            <span className="step-card__meta">
                                {step.action} · {formatDuration(step.started_at, step.completed_at)}
                            </span>
                        </div>
                    </div>
                    <div className="step-card__right">
                        <StatusBadge status={step.status} size="sm" />
                        {step.result_payload && (
                            <span className="step-card__expand">{expanded ? '▾' : '▸'}</span>
                        )}
                    </div>
                </div>

                {step.depends_on.length > 0 && (
                    <div className="step-card__deps">
                        Depends on: {step.depends_on.join(', ')}
                    </div>
                )}

                {expanded && step.result_payload && (
                    <div className="step-card__payload">
                        <pre>{JSON.stringify(step.result_payload, null, 2)}</pre>
                    </div>
                )}
            </div>
        </div>
    );
}

export function RunDetailPage() {
    const { id } = useParams<{ id: string }>();
    const navigate = useNavigate();
    const [state, setState] = useState<WorkflowStateResponse | null>(null);
    const [error, setError] = useState<string | null>(null);
    const statusRef = useRef<string | null>(null);

    const fetchState = useCallback(async () => {
        if (!id) return;
        try {
            const data = await getWorkflowState(id);
            setState(data);
            statusRef.current = data.status;
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to fetch state');
        }
    }, [id]);

    useEffect(() => {
        fetchState();
        const interval = setInterval(() => {
            // Only poll while workflow is actively executing
            if (statusRef.current === 'COMPLETED' || statusRef.current === 'FAILED') {
                clearInterval(interval);
                return;
            }
            fetchState();
        }, 1000);
        return () => clearInterval(interval);
    }, [fetchState]);

    if (error) {
        return (
            <div className="page">
                <div className="error-banner">
                    <span className="error-banner__icon">⚠</span>
                    {error}
                </div>
            </div>
        );
    }

    if (!state) {
        return (
            <div className="page">
                <div className="loading-state">
                    <span className="spinner spinner--lg" />
                    <p>Loading workflow…</p>
                </div>
            </div>
        );
    }

    const sortedSteps = topoSort(state.steps);
    const completedSteps = sortedSteps.filter((s) => s.status === 'COMPLETED').length;
    const totalDuration = formatDuration(state.created_at, state.completed_at);

    return (
        <div className="page">
            <button className="btn btn--ghost" onClick={() => navigate('/')}>
                ← Back to Dashboard
            </button>

            <div className="run-header">
                <div className="run-header__top">
                    <h1 className="run-header__title">{state.name}</h1>
                    <StatusBadge status={state.status} />
                </div>
                <div className="run-header__meta">
                    <span className="run-header__stat">
                        <span className="run-header__label">ID</span>
                        {state.workflow_id.slice(0, 8)}…
                    </span>
                    <span className="run-header__stat">
                        <span className="run-header__label">Progress</span>
                        {completedSteps}/{state.steps.length} steps
                    </span>
                    <span className="run-header__stat">
                        <span className="run-header__label">Duration</span>
                        {totalDuration}
                    </span>
                    <span className="run-header__stat">
                        <span className="run-header__label">Started</span>
                        {formatTimestamp(state.created_at)}
                    </span>
                </div>
            </div>

            <div className="timeline">
                {sortedSteps.map((step, i) => (
                    <StepCard key={step.step_id} step={step} index={i} />
                ))}
            </div>
        </div>
    );
}
