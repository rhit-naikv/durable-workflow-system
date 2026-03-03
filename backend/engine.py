"""
DBOS Durable Execution Engine for the Workflow System.

Contains the @DBOS.workflow() DAG resolver and @DBOS.step() task executor.
Implements Kahn's algorithm for topological ordering and dispatches
simulated AI tasks with durable checkpointing.
"""

import time
import random
from collections import deque
from collections.abc import Callable

from dbos import DBOS

from database import update_step_status, update_workflow_status
from models import StepStatus, WorkflowStatus


# ── Simulated AI Task Functions ────────────────────────────────────────────────

def sim_validate_order(params: dict) -> dict:
    """Simulate validating an order (assignment example action)."""
    time.sleep(random.uniform(0.5, 1.5))
    return {
        "validation_passed": True,
        "order_id": params.get("order_id", "ORD-001"),
        "checks": ["inventory", "payment", "address"],
    }


def sim_fetch_dataset(params: dict) -> dict:
    """Simulate fetching a dataset from an external source."""
    source = params.get("source", "s3://default-bucket/data")
    time.sleep(random.uniform(1.0, 2.0))
    return {
        "source": source,
        "rows_fetched": random.randint(1000, 50000),
        "schema": ["id", "text", "label", "timestamp"],
        "size_mb": round(random.uniform(5.0, 500.0), 1),
    }


def sim_generate_prompt(params: dict) -> dict:
    """Simulate generating a prompt from a template."""
    template = params.get("template", "Summarize the following data: {data}")
    time.sleep(random.uniform(0.5, 1.5))
    return {
        "template_used": template,
        "generated_prompt": f"Based on the ingested dataset, {template.lower()}",
        "token_count": random.randint(50, 200),
    }


def sim_call_llm(params: dict) -> dict:
    """Simulate calling an LLM API."""
    model = params.get("model", "gpt-4")
    time.sleep(random.uniform(2.0, 3.0))
    return {
        "model": model,
        "response": "The dataset contains structured records spanning Q1-Q3 2025. "
                    "Key patterns include a 23% increase in user engagement and "
                    "a notable shift in content preferences toward video formats.",
        "tokens_used": random.randint(100, 500),
        "latency_ms": random.randint(800, 3000),
    }


def sim_validate_output(params: dict) -> dict:
    """Simulate validating an LLM output."""
    time.sleep(random.uniform(0.5, 1.0))
    return {
        "validation_passed": True,
        "confidence_score": round(random.uniform(0.85, 0.99), 3),
        "checks_run": ["format_check", "factual_consistency", "tone_analysis"],
    }


def sim_store_results(params: dict) -> dict:
    """Simulate storing results to a destination."""
    destination = params.get("destination", "postgres")
    time.sleep(random.uniform(0.5, 1.5))
    return {
        "destination": destination,
        "records_written": random.randint(1, 10),
        "storage_path": f"{destination}://results/run_{random.randint(1000, 9999)}",
    }


# Action dispatcher mapping — maps config.action values to handler functions
TASK_REGISTRY: dict[str, Callable] = {
    "validate_order": sim_validate_order,
    "fetch_dataset": sim_fetch_dataset,
    "generate_prompt": sim_generate_prompt,
    "call_llm": sim_call_llm,
    "validate_output": sim_validate_output,
    "store_results": sim_store_results,
}


def sim_generic_task(params: dict) -> dict:
    """Fallback for unknown action types."""
    time.sleep(random.uniform(1.0, 2.0))
    return {"status": "completed", "params_received": params}


# ── DBOS Step (Durable Task Executor) ──────────────────────────────────────────

@DBOS.step()
def execute_step(workflow_id: str, step_id: str, step_name: str, action: str, params: dict) -> dict:
    """
    Execute a single workflow step. This is wrapped in @DBOS.step() so the
    return value is durably checkpointed to Postgres. On crash recovery,
    DBOS will skip re-execution and replay the cached result.
    """
    # Mark step as RUNNING in the application database
    update_step_status(workflow_id, step_id, StepStatus.RUNNING)

    try:
        # Dispatch to the appropriate simulated task
        task_fn = TASK_REGISTRY.get(action, sim_generic_task)
        result = task_fn(params)

        # Mark step as COMPLETED with result payload
        update_step_status(workflow_id, step_id, StepStatus.COMPLETED, result_payload=result)

        return result

    except Exception as e:
        # Mark step as FAILED
        update_step_status(
            workflow_id, step_id, StepStatus.FAILED,
            result_payload={"error": str(e)}
        )
        raise


# ── DBOS Workflow (DAG Resolver) ───────────────────────────────────────────────

@DBOS.workflow()
def execute_workflow(workflow_id: str, definition_dict: dict):
    """
    Parse the DAG, resolve dependencies via Kahn's algorithm, and execute
    steps in topological order. This entire function is wrapped in
    @DBOS.workflow() — on crash recovery, DBOS replays from the beginning
    but skips already-completed @DBOS.step() calls using cached results.
    """
    steps = definition_dict["steps"]

    # Mark workflow as RUNNING
    update_workflow_status(workflow_id, WorkflowStatus.RUNNING)

    # NOTE: depends_on references and cycle detection are validated at
    # submission time by the Pydantic model_validator on WorkflowDefinition.
    # The post-Kahn check below is kept as a defensive safety net.

    # Build adjacency structures for Kahn's algorithm
    # in_degree[step_id] = number of unresolved dependencies
    # dependents[step_id] = list of step_ids that depend on this step
    in_degree: dict[str, int] = {}
    dependents: dict[str, list[str]] = {}
    step_map: dict[str, dict] = {}

    for step in steps:
        sid = step["id"]
        step_map[sid] = step
        in_degree[sid] = len(step.get("depends_on", []))
        dependents[sid] = []

    for step in steps:
        for dep in step.get("depends_on", []):
            if dep in dependents:
                dependents[dep].append(step["id"])

    # Kahn's algorithm: process steps whose dependencies are all resolved
    queue: deque[str] = deque()
    for sid, degree in in_degree.items():
        if degree == 0:
            queue.append(sid)

    completed_count = 0
    total_steps = len(steps)

    try:
        while queue:
            # Process all currently unblocked steps in this tier.
            # NOTE (V1): Steps within the same tier are executed sequentially
            # here for simplicity. In a V2 implementation, these could be
            # dispatched concurrently via asyncio.gather() or distributed
            # across a worker pool for true parallel execution.
            current_tier = list(queue)
            queue.clear()

            for step_id in current_tier:
                step = step_map[step_id]

                # Execute the step (durable via @DBOS.step)
                execute_step(
                    workflow_id=workflow_id,
                    step_id=step_id,
                    step_name=step["name"],
                    action=step["config"]["action"],
                    params=step["config"].get("params", {}),
                )

                completed_count += 1

                # Unblock dependents
                for dependent_id in dependents.get(step_id, []):
                    in_degree[dependent_id] -= 1
                    if in_degree[dependent_id] == 0:
                        queue.append(dependent_id)

        # Check if all steps completed (safety net — cycles are rejected at
        # submission time by the Pydantic model_validator)
        if completed_count == total_steps:
            update_workflow_status(workflow_id, WorkflowStatus.COMPLETED)
        else:
            # Some steps never became unblocked — likely a cycle
            update_workflow_status(workflow_id, WorkflowStatus.FAILED)

    except Exception:
        update_workflow_status(workflow_id, WorkflowStatus.FAILED)
        raise
