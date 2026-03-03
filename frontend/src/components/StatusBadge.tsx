import { type StepStatus, type WorkflowStatus } from '../api';

const STATUS_CONFIG: Record<StepStatus | WorkflowStatus, { label: string; className: string; icon: string }> = {
    PENDING: {
        label: 'Pending',
        className: 'badge--pending',
        icon: '○',
    },
    RUNNING: {
        label: 'Running',
        className: 'badge--running',
        icon: '◉',
    },
    COMPLETED: {
        label: 'Completed',
        className: 'badge--completed',
        icon: '✓',
    },
    FAILED: {
        label: 'Failed',
        className: 'badge--failed',
        icon: '✕',
    },
};

interface StatusBadgeProps {
    status: StepStatus | WorkflowStatus;
    size?: 'sm' | 'md';
}

export function StatusBadge({ status, size = 'md' }: StatusBadgeProps) {
    const config = STATUS_CONFIG[status];
    return (
        <span className={`badge ${config.className} ${size === 'sm' ? 'badge--sm' : ''}`}>
            <span className="badge__icon">{config.icon}</span>
            {config.label}
        </span>
    );
}
