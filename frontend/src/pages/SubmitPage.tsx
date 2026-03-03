import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { submitWorkflow } from '../api';

const EXAMPLE_PAYLOAD = JSON.stringify(
    {
        name: 'AI Data Pipeline',
        steps: [
            {
                id: 'fetch',
                type: 'task',
                config: { action: 'fetch_dataset', params: { source: 's3://ml-datasets/customer-reviews' } },
                depends_on: [],
            },
            {
                id: 'prompt',
                type: 'task',
                config: { action: 'generate_prompt', params: { template: 'Summarize the key insights from: {data}' } },
                depends_on: ['fetch'],
            },
            {
                id: 'llm',
                type: 'task',
                config: { action: 'call_llm', params: { model: 'gpt-4' } },
                depends_on: ['prompt'],
            },
            {
                id: 'validate',
                type: 'task',
                config: { action: 'validate_output', params: {} },
                depends_on: ['llm'],
            },
            {
                id: 'store',
                type: 'task',
                config: { action: 'store_results', params: { destination: 'postgres' } },
                depends_on: ['validate'],
            },
        ],
    },
    null,
    2
);

export function SubmitPage() {
    const navigate = useNavigate();
    const [json, setJson] = useState(EXAMPLE_PAYLOAD);
    const [error, setError] = useState<string | null>(null);
    const [submitting, setSubmitting] = useState(false);

    const handleSubmit = async () => {
        setError(null);

        // Validate JSON
        let parsed;
        try {
            parsed = JSON.parse(json);
        } catch {
            setError('Invalid JSON — please check your syntax.');
            return;
        }

        setSubmitting(true);
        try {
            const result = await submitWorkflow(parsed);
            navigate(`/runs/${result.workflow_id}`);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Submission failed');
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <div className="page">
            <div className="page__header">
                <h1 className="page__title">Submit Pipeline</h1>
                <p className="page__subtitle">
                    Paste your JSON workflow definition below. The engine will parse the DAG and
                    execute steps in topological order with durable checkpointing.
                </p>
            </div>

            <div className="editor-card">
                <div className="editor-card__header">
                    <span className="editor-card__dot editor-card__dot--red" />
                    <span className="editor-card__dot editor-card__dot--yellow" />
                    <span className="editor-card__dot editor-card__dot--green" />
                    <span className="editor-card__label">workflow.json</span>
                </div>
                <textarea
                    id="json-editor"
                    className="editor-card__textarea"
                    value={json}
                    onChange={(e) => setJson(e.target.value)}
                    spellCheck={false}
                    rows={22}
                />
            </div>

            {error && (
                <div className="error-banner" role="alert">
                    <span className="error-banner__icon">⚠</span>
                    {error}
                </div>
            )}

            <button
                id="submit-pipeline-btn"
                className="btn btn--primary"
                onClick={handleSubmit}
                disabled={submitting}
            >
                {submitting ? (
                    <>
                        <span className="spinner" /> Submitting…
                    </>
                ) : (
                    'Submit Pipeline →'
                )}
            </button>
        </div>
    );
}
