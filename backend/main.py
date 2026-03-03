"""
FastAPI application for the Durable Workflow Execution System.

Exposes REST endpoints to submit JSON DAGs and query execution state.
DBOS Transact provides durable execution guarantees via PostgreSQL.
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dbos import DBOS, DBOSConfig

# Import engine so DBOS discovers the @DBOS.workflow/@DBOS.step decorators
import engine  # noqa: F401

from models import (
    WorkflowDefinition,
    WorkflowRunResponse,
    WorkflowStateResponse,
    WorkflowSummaryResponse,
    StepStatusResponse,
    WorkflowStatus,
)
from database import (
    init_db,
    create_workflow_run,
    list_workflow_runs,
    get_workflow_state,
)


# ── FastAPI Setup ──────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize application database tables on server start."""
    init_db()
    yield


app = FastAPI(title="Durable Workflow Engine", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── DBOS Setup ─────────────────────────────────────────────────────────────────

db_url = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:dbos_password@postgres:5432/workflow_db"
)

config: DBOSConfig = {
    "name": "workflow-engine",
    "system_database_url": db_url,
}

DBOS(fastapi=app, config=config)


# ── API Endpoints ──────────────────────────────────────────────────────────────

@app.get("/api/health")
def health_check():
    """Health check endpoint."""
    return {
        "status": "online",
        "message": "FastAPI and DBOS are successfully connected to PostgreSQL!",
    }


@app.post("/api/workflows", response_model=WorkflowRunResponse)
def submit_workflow(definition: WorkflowDefinition):
    """
    Accept a JSON DAG workflow definition, persist it to Postgres,
    then start the DBOS durable workflow for async execution.
    """
    # Convert steps to dicts for the database layer
    steps_data = [step.model_dump() for step in definition.steps]
    definition_dict = definition.model_dump()

    workflow_id = create_workflow_run(
        name=definition.name,
        definition=definition_dict,
        steps=steps_data,
    )

    # Start the DBOS workflow in the background (durable, crash-recoverable)
    DBOS.start_workflow(engine.execute_workflow, workflow_id, definition_dict)

    return WorkflowRunResponse(workflow_id=workflow_id)


@app.get("/api/workflows", response_model=list[WorkflowSummaryResponse])
def list_workflows():
    """Return a list of all workflow runs with summary status."""
    rows = list_workflow_runs()
    return [
        WorkflowSummaryResponse(
            workflow_id=str(row["workflow_id"]),
            name=row["name"],
            status=WorkflowStatus(row["status"]),
            created_at=row["created_at"],
            completed_at=row["completed_at"],
            total_steps=row["total_steps"],
            completed_steps=row["completed_steps"],
        )
        for row in rows
    ]


@app.get("/api/workflows/{workflow_id}/state", response_model=WorkflowStateResponse)
def get_workflow_state_endpoint(workflow_id: str):
    """Return the full state of a workflow run, including all step statuses."""
    # Validate UUID format to avoid Postgres errors on malformed IDs
    try:
        import uuid
        uuid.UUID(workflow_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Workflow not found")

    state = get_workflow_state(workflow_id)
    if not state:
        raise HTTPException(status_code=404, detail="Workflow not found")

    return WorkflowStateResponse(
        workflow_id=str(state["workflow_id"]),
        name=state["name"],
        status=WorkflowStatus(state["status"]),
        created_at=state["created_at"],
        completed_at=state["completed_at"],
        steps=[
            StepStatusResponse(
                step_id=step["step_id"],
                step_name=step["step_name"],
                status=step["status"],
                action=step["action"],
                depends_on=step["depends_on"] if isinstance(step["depends_on"], list) else [],
                result_payload=step["result_payload"],
                started_at=step["started_at"],
                completed_at=step["completed_at"],
            )
            for step in state["steps"]
        ],
    )
