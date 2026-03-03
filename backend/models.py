"""
Pydantic models for the Durable Workflow Execution System.

Defines the JSON DAG contract (input) and API response schemas (output).
The input contract matches the assignment's JSON format:
  - steps use "type" (e.g. "task") and "config.action" (e.g. "validate_order")
  - "name" on steps is optional (defaults to step id)
"""

from enum import Enum
from datetime import datetime
from collections import deque

from pydantic import BaseModel, Field, model_validator


# ── Enums ──────────────────────────────────────────────────────────────────────

class StepStatus(str, Enum):
    """Execution status for an individual workflow step."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class WorkflowStatus(str, Enum):
    """Overall execution status for a workflow run."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


# ── Input Models (JSON DAG Contract) ───────────────────────────────────────────

class StepConfig(BaseModel):
    """Configuration for a single task within a workflow step."""
    action: str = Field(..., description="Action identifier, e.g. 'validate_order', 'fetch_dataset'")
    params: dict = Field(default_factory=dict, description="Arbitrary parameters for the task")


class WorkflowStep(BaseModel):
    """A single step/node in the workflow DAG."""
    id: str = Field(..., description="Unique identifier for this step within the workflow")
    name: str | None = Field(default=None, description="Human-readable name for the step (defaults to id)")
    type: str = Field(default="task", description="Step type classification, e.g. 'task'")
    config: StepConfig = Field(..., description="Task configuration for execution")
    depends_on: list[str] = Field(default_factory=list, description="List of step IDs this step depends on")

    @model_validator(mode="after")
    def default_name_to_id(self):
        """If no name is provided, fall back to the step id."""
        if self.name is None:
            self.name = self.id
        return self


class WorkflowDefinition(BaseModel):
    """The full JSON DAG payload submitted to create a workflow."""
    name: str = Field(..., description="Human-readable name for the workflow")
    steps: list[WorkflowStep] = Field(..., min_length=1, description="Ordered list of steps in the DAG")

    @model_validator(mode="after")
    def validate_dag(self):
        """
        Pre-execution DAG validation using Kahn's algorithm.
        Rejects the payload with a clear error before any database insertion
        if the graph contains duplicate IDs, invalid references, or cycles.
        """
        # 1. Check for duplicate step IDs
        seen_ids: set[str] = set()
        for step in self.steps:
            if step.id in seen_ids:
                raise ValueError(
                    f"Duplicate step id '{step.id}' — each step must have a unique id"
                )
            seen_ids.add(step.id)

        # 2. Validate depends_on references
        for step in self.steps:
            for dep in step.depends_on:
                if dep not in seen_ids:
                    raise ValueError(
                        f"Step '{step.id}' depends on unknown step '{dep}'"
                    )

        # 3. Cycle detection via Kahn's algorithm
        in_degree: dict[str, int] = {}
        dependents: dict[str, list[str]] = {}

        for step in self.steps:
            in_degree[step.id] = len(step.depends_on)
            dependents[step.id] = []

        for step in self.steps:
            for dep in step.depends_on:
                dependents[dep].append(step.id)

        queue: deque[str] = deque(
            sid for sid, degree in in_degree.items() if degree == 0
        )
        sorted_count = 0

        while queue:
            sid = queue.popleft()
            sorted_count += 1
            for dependent_id in dependents[sid]:
                in_degree[dependent_id] -= 1
                if in_degree[dependent_id] == 0:
                    queue.append(dependent_id)

        if sorted_count < len(self.steps):
            raise ValueError(
                "Workflow contains a cyclic dependency — "
                "all steps must form a valid DAG (no circular depends_on chains)"
            )

        return self


# ── Response Models ────────────────────────────────────────────────────────────

class WorkflowRunResponse(BaseModel):
    """Response returned after submitting a new workflow."""
    workflow_id: str


class StepStatusResponse(BaseModel):
    """Status of an individual step within a workflow run."""
    step_id: str
    step_name: str
    status: StepStatus
    action: str
    depends_on: list[str]
    result_payload: dict | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


class WorkflowStateResponse(BaseModel):
    """Full state of a workflow run, including all step statuses."""
    workflow_id: str
    name: str
    status: WorkflowStatus
    created_at: datetime
    completed_at: datetime | None = None
    steps: list[StepStatusResponse]


class WorkflowSummaryResponse(BaseModel):
    """Summary of a workflow run for the list/dashboard view."""
    workflow_id: str
    name: str
    status: WorkflowStatus
    created_at: datetime
    completed_at: datetime | None = None
    total_steps: int
    completed_steps: int
