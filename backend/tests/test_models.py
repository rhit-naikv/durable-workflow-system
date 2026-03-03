import pytest
from pydantic import ValidationError

from models import WorkflowDefinition, WorkflowStep


def test_valid_linear_dag():
    data = {
        "name": "Linear Test",
        "steps": [
            {
                "id": "A",
                "type": "task",
                "config": {"action": "validate_order", "params": {}},
                "depends_on": []
            },
            {
                "id": "B",
                "type": "task",
                "config": {"action": "validate_output", "params": {}},
                "depends_on": ["A"]
            }
        ]
    }
    workflow = WorkflowDefinition(**data)
    assert workflow.name == "Linear Test"
    assert len(workflow.steps) == 2


def test_name_defaults_to_id():
    data = {
        "id": "fetch_data",
        "type": "task",
        "config": {"action": "fetch_dataset", "params": {}},
        "depends_on": []
    }
    step = WorkflowStep(**data)
    assert step.name == "fetch_data"


def test_duplicate_step_ids_rejected():
    data = {
        "name": "Duplicate IDs",
        "steps": [
            {"id": "A", "config": {"action": "x", "params": {}}, "depends_on": []},
            {"id": "A", "config": {"action": "y", "params": {}}, "depends_on": []},
        ]
    }
    with pytest.raises(ValidationError) as exc_info:
        WorkflowDefinition(**data)
    
    assert "Duplicate step id 'A'" in str(exc_info.value)


def test_invalid_depends_on_reference():
    data = {
        "name": "Invalid Ref",
        "steps": [
            {"id": "A", "config": {"action": "x", "params": {}}, "depends_on": ["B"]},
        ]
    }
    with pytest.raises(ValidationError) as exc_info:
        WorkflowDefinition(**data)
    
    assert "depends on unknown step 'B'" in str(exc_info.value)


def test_cycle_detected():
    data = {
        "name": "Cyclic DAG",
        "steps": [
            {"id": "A", "config": {"action": "x", "params": {}}, "depends_on": ["B"]},
            {"id": "B", "config": {"action": "y", "params": {}}, "depends_on": ["A"]},
        ]
    }
    with pytest.raises(ValidationError) as exc_info:
        WorkflowDefinition(**data)
    
    assert "cyclic dependency" in str(exc_info.value).lower()


def test_parallel_dag_valid():
    """Two independent tasks depending on nothing should be valid."""
    data = {
        "name": "Parallel Root DAG",
        "steps": [
            {"id": "A", "config": {"action": "x", "params": {}}, "depends_on": []},
            {"id": "B", "config": {"action": "y", "params": {}}, "depends_on": []},
        ]
    }
    workflow = WorkflowDefinition(**data)
    assert len(workflow.steps) == 2


def test_empty_steps_rejected():
    data = {
        "name": "Empty Steps",
        "steps": []
    }
    with pytest.raises(ValidationError) as exc_info:
        WorkflowDefinition(**data)
    
    assert "List should have at least 1 item" in str(exc_info.value)
