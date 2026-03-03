"""
PostgreSQL-backed state store for the Durable Workflow Execution System.

Uses raw psycopg (v3) queries against the same Postgres instance used by DBOS.
Tables are auto-created on startup via CREATE TABLE IF NOT EXISTS.
Connection pooling is used to avoid exhausting Postgres connection limits.
"""

import os
import json
import uuid
from datetime import datetime, timezone

import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from models import StepStatus, WorkflowStatus


def get_connection_string() -> str:
    """Get the Postgres connection string from the environment."""
    return os.environ.get(
        "DATABASE_URL",
        "postgresql://postgres:dbos_password@postgres:5432/workflow_db"
    )


# ── Connection Pool ───────────────────────────────────────────────────────────

_pool: ConnectionPool | None = None


def get_pool() -> ConnectionPool:
    """Get or create the module-level connection pool."""
    global _pool
    if _pool is None:
        _pool = ConnectionPool(
            conninfo=get_connection_string(),
            min_size=2,
            max_size=10,
            kwargs={"row_factory": dict_row},
        )
    return _pool


def get_connection():
    """Get a connection from the pool (use as context manager)."""
    return get_pool().connection()


# ── Schema Initialization ─────────────────────────────────────────────────────

def init_db():
    """Create application tables if they don't exist."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS workflows (
                    id UUID PRIMARY KEY,
                    name TEXT NOT NULL,
                    raw_definition JSONB NOT NULL,
                    status TEXT NOT NULL DEFAULT 'PENDING',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    completed_at TIMESTAMPTZ
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS step_executions (
                    id UUID PRIMARY KEY,
                    workflow_id UUID NOT NULL REFERENCES workflows(id) ON DELETE CASCADE,
                    step_node_id TEXT NOT NULL,
                    step_name TEXT NOT NULL,
                    action TEXT NOT NULL,
                    depends_on JSONB NOT NULL DEFAULT '[]',
                    status TEXT NOT NULL DEFAULT 'PENDING',
                    result_payload JSONB,
                    started_at TIMESTAMPTZ,
                    completed_at TIMESTAMPTZ
                );
            """)
            # Index for fast lookups by workflow_id
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_step_executions_workflow_id
                ON step_executions(workflow_id);
            """)
        conn.commit()


# ── Workflow CRUD ──────────────────────────────────────────────────────────────

def create_workflow_run(name: str, definition: dict, steps: list[dict]) -> str:
    """
    Insert a new workflow run and its initial PENDING step rows.
    Returns the generated workflow_id.
    """
    workflow_id = str(uuid.uuid4())

    with get_connection() as conn:
        with conn.cursor() as cur:
            # Insert the workflow
            cur.execute(
                """
                INSERT INTO workflows (id, name, raw_definition, status, created_at)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (workflow_id, name, json.dumps(definition), WorkflowStatus.PENDING, datetime.now(timezone.utc))
            )

            # Insert all steps as PENDING
            for step in steps:
                step_exec_id = str(uuid.uuid4())
                cur.execute(
                    """
                    INSERT INTO step_executions (id, workflow_id, step_node_id, step_name, action, depends_on, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        step_exec_id,
                        workflow_id,
                        step["id"],
                        step["name"],
                        step["config"]["action"],
                        json.dumps(step.get("depends_on", [])),
                        StepStatus.PENDING,
                    )
                )

        conn.commit()

    return workflow_id


def list_workflow_runs() -> list[dict]:
    """Return a summary list of all workflow runs, newest first."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    w.id AS workflow_id,
                    w.name,
                    w.status,
                    w.created_at,
                    w.completed_at,
                    COUNT(se.id) AS total_steps,
                    COUNT(se.id) FILTER (WHERE se.status = 'COMPLETED') AS completed_steps
                FROM workflows w
                LEFT JOIN step_executions se ON se.workflow_id = w.id
                GROUP BY w.id
                ORDER BY w.created_at DESC
                """
            )
            return cur.fetchall()


def get_workflow_state(workflow_id: str) -> dict | None:
    """
    Get the full state of a workflow run, including all step statuses.
    Returns None if the workflow is not found.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            # Get workflow header
            cur.execute(
                "SELECT id AS workflow_id, name, status, created_at, completed_at FROM workflows WHERE id = %s",
                (workflow_id,)
            )
            workflow = cur.fetchone()
            if not workflow:
                return None

            # Get all steps for this workflow
            cur.execute(
                """
                SELECT
                    step_node_id AS step_id,
                    step_name,
                    status,
                    action,
                    depends_on,
                    result_payload,
                    started_at,
                    completed_at
                FROM step_executions
                WHERE workflow_id = %s
                """,
                (workflow_id,)
            )
            steps = cur.fetchall()

            workflow["steps"] = steps
            return workflow


# ── Step Status Updates ────────────────────────────────────────────────────────

def update_step_status(
    workflow_id: str,
    step_node_id: str,
    status: StepStatus,
    result_payload: dict | None = None,
):
    """Update the status of a specific step within a workflow."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            now = datetime.now(timezone.utc)

            if status == StepStatus.RUNNING:
                cur.execute(
                    """
                    UPDATE step_executions
                    SET status = %s, started_at = %s
                    WHERE workflow_id = %s AND step_node_id = %s
                    """,
                    (status, now, workflow_id, step_node_id)
                )
            elif status in (StepStatus.COMPLETED, StepStatus.FAILED):
                cur.execute(
                    """
                    UPDATE step_executions
                    SET status = %s, completed_at = %s, result_payload = %s
                    WHERE workflow_id = %s AND step_node_id = %s
                    """,
                    (status, now, json.dumps(result_payload) if result_payload else None, workflow_id, step_node_id)
                )
            else:
                cur.execute(
                    """
                    UPDATE step_executions
                    SET status = %s
                    WHERE workflow_id = %s AND step_node_id = %s
                    """,
                    (status, workflow_id, step_node_id)
                )

        conn.commit()


def update_workflow_status(workflow_id: str, status: WorkflowStatus):
    """Update the overall workflow status."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            if status in (WorkflowStatus.COMPLETED, WorkflowStatus.FAILED):
                cur.execute(
                    """
                    UPDATE workflows
                    SET status = %s, completed_at = %s
                    WHERE id = %s
                    """,
                    (status, datetime.now(timezone.utc), workflow_id)
                )
            else:
                cur.execute(
                    "UPDATE workflows SET status = %s WHERE id = %s",
                    (status, workflow_id)
                )
        conn.commit()
