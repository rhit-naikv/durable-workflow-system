import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { listWorkflows, type WorkflowSummaryResponse } from '../api';
import { StatusBadge } from '../components/StatusBadge';

function formatTime(iso: string): string {
    return new Date(iso).toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
    });
}

function formatDuration(created: string, completed: string | null): string {
    if (!completed) return '—';
    const ms = new Date(completed).getTime() - new Date(created).getTime();
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(1)}s`;
}

export function DashboardPage() {
    const navigate = useNavigate();
    const [workflows, setWorkflows] = useState<WorkflowSummaryResponse[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        let active = true;
        const fetchData = async () => {
            try {
                const data = await listWorkflows();
                if (active) {
                    setWorkflows(data);
                    setError(null);
                }
            } catch (err) {
                if (active) {
                    setError(err instanceof Error ? err.message : 'Failed to load workflows');
                }
            } finally {
                if (active) setLoading(false);
            }
        };

        fetchData();
        const interval = setInterval(fetchData, 5000);
        return () => {
            active = false;
            clearInterval(interval);
        };
    }, []);

    return (
        <div className="page">
            <div className="page__header">
                <h1 className="page__title">Pipeline Runs</h1>
                <p className="page__subtitle">Historical and active workflow executions</p>
            </div>

            {error && (
                <div className="error-banner" role="alert">
                    <span className="error-banner__icon">⚠</span>
                    {error}
                </div>
            )}

            {loading ? (
                <div className="loading-state">
                    <span className="spinner spinner--lg" />
                    <p>Loading runs…</p>
                </div>
            ) : workflows.length === 0 && !error ? (
                <div className="empty-state">
                    <div className="empty-state__icon">⬡</div>
                    <h2>No pipeline runs yet</h2>
                    <p>Submit your first workflow to see it appear here.</p>
                    <button className="btn btn--primary" onClick={() => navigate('/submit')}>
                        Submit Pipeline →
                    </button>
                </div>
            ) : (
                <div className="table-container">
                    <table className="data-table">
                        <thead>
                            <tr>
                                <th>Workflow ID</th>
                                <th>Name</th>
                                <th>Status</th>
                                <th>Progress</th>
                                <th>Started</th>
                                <th>Duration</th>
                            </tr>
                        </thead>
                        <tbody>
                            {workflows.map((wf) => (
                                <tr
                                    key={wf.workflow_id}
                                    className="data-table__row"
                                    onClick={() => navigate(`/runs/${wf.workflow_id}`)}
                                >
                                    <td className="data-table__id">{wf.workflow_id.slice(0, 8)}…</td>
                                    <td>{wf.name}</td>
                                    <td>
                                        <StatusBadge status={wf.status} size="sm" />
                                    </td>
                                    <td>
                                        <div className="progress-bar">
                                            <div
                                                className="progress-bar__fill"
                                                style={{ width: `${(wf.completed_steps / wf.total_steps) * 100}%` }}
                                            />
                                        </div>
                                        <span className="progress-bar__label">
                                            {wf.completed_steps}/{wf.total_steps}
                                        </span>
                                    </td>
                                    <td>{formatTime(wf.created_at)}</td>
                                    <td>{formatDuration(wf.created_at, wf.completed_at)}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
}
