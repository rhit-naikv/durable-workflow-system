import pytest
import engine
from models import WorkflowStatus, StepStatus

def test_sim_validate_order(mocker):
    mocker.patch("engine.time.sleep")
    result = engine.sim_validate_order({"order_id": "ORD-123"})
    assert result["validation_passed"] is True
    assert result["order_id"] == "ORD-123"
    assert "checks" in result

def test_sim_fetch_dataset_uses_source_param(mocker):
    mocker.patch("engine.time.sleep")
    result = engine.sim_fetch_dataset({"source": "s3://test/data"})
    assert result["source"] == "s3://test/data"
    assert "rows_fetched" in result

def test_sim_generate_prompt_uses_template(mocker):
    mocker.patch("engine.time.sleep")
    result = engine.sim_generate_prompt({"template": "My template {data}"})
    assert result["template_used"] == "My template {data}"
    assert "My template {data}".lower() in result["generated_prompt"]

def test_sim_call_llm_uses_model_param(mocker):
    mocker.patch("engine.time.sleep")
    result = engine.sim_call_llm({"model": "gpt-3.5"})
    assert result["model"] == "gpt-3.5"
    assert "response" in result

def test_sim_validate_output(mocker):
    mocker.patch("engine.time.sleep")
    result = engine.sim_validate_output({})
    assert result["validation_passed"] is True
    assert "confidence_score" in result

def test_sim_store_results_uses_destination(mocker):
    mocker.patch("engine.time.sleep")
    result = engine.sim_store_results({"destination": "mysql"})
    assert result["destination"] == "mysql"
    assert "records_written" in result

def test_sim_generic_task_echoes_params(mocker):
    mocker.patch("engine.time.sleep")
    params = {"foo": "bar"}
    result = engine.sim_generic_task(params)
    assert result["status"] == "completed"
    assert result["params_received"] == params

def test_task_registry_has_all_known_actions():
    expected_actions = {
        "validate_order",
        "fetch_dataset",
        "generate_prompt",
        "call_llm",
        "validate_output",
        "store_results",
    }
    assert set(engine.TASK_REGISTRY.keys()) == expected_actions

# -- Testing engine DBOS decorators --

def test_execute_step_success(mocker):
    mock_update_step = mocker.patch("engine.update_step_status")
    
    # We can call the original function wrapped by DBOS.step
    # Note: DBOS step mock can be bypassed by importing the underlying function or calling it during test.
    # However since the logic is inside the function body, calling it directly works inside tests if DBOS is mocked.
    mocker.patch("dbos.DBOS.step", lambda *a, **k: lambda f: f)
    # Re-apply wrapper mock manually for testing since it's applied at import time
    from engine import execute_step
    
    # mock a task fn
    mocker.patch.dict("engine.TASK_REGISTRY", {"test_action": lambda p: {"ok": 1}})
    
    res = execute_step.__wrapped__("wf_1", "step_A", "Step A", "test_action", {})
    assert res == {"ok": 1}
    
    # Should update step to RUNNING then COMPLETED
    assert mock_update_step.call_args_list[0][0][2] == StepStatus.RUNNING
    assert mock_update_step.call_args_list[1][0][2] == StepStatus.COMPLETED

def test_execute_step_failure(mocker):
    mock_update_step = mocker.patch("engine.update_step_status")
    
    def failing_task(p):
        raise ValueError("Simulated crash")
        
    mocker.patch.dict("engine.TASK_REGISTRY", {"bad_action": failing_task})
    from engine import execute_step
    
    with pytest.raises(ValueError):
        execute_step.__wrapped__("wf_1", "step_B", "Step B", "bad_action", {})
        
    assert mock_update_step.call_args_list[0][0][2] == StepStatus.RUNNING
    assert mock_update_step.call_args_list[1][0][2] == StepStatus.FAILED

def test_execute_workflow_success(mocker):
    mock_update_wf = mocker.patch("engine.update_workflow_status")
    mock_execute_step = mocker.patch("engine.execute_step")
    
    def_dict = {
        "steps": [
            {"id": "A", "name": "A", "config": {"action": "x", "params": {}}, "depends_on": []},
            {"id": "B", "name": "B", "config": {"action": "y", "params": {}}, "depends_on": ["A"]},
        ]
    }
    
    from engine import execute_workflow
    execute_workflow.__wrapped__("wf_1", def_dict)
    
    assert mock_execute_step.call_count == 2
    # Ensure they were called in order: A then B
    assert mock_execute_step.call_args_list[0].kwargs["step_id"] == "A"
    assert mock_execute_step.call_args_list[1].kwargs["step_id"] == "B"
    
    assert mock_update_wf.call_args_list[0][0][1] == WorkflowStatus.RUNNING
    assert mock_update_wf.call_args_list[1][0][1] == WorkflowStatus.COMPLETED

def test_execute_workflow_unprocessed_cycle(mocker):
    mock_update_wf = mocker.patch("engine.update_workflow_status")
    mock_execute_step = mocker.patch("engine.execute_step")
    
    def_dict = {
        "steps": [
            {"id": "A", "name": "A", "config": {"action": "x", "params": {}}, "depends_on": ["B"]},
            {"id": "B", "name": "B", "config": {"action": "y", "params": {}}, "depends_on": ["A"]},
        ]
    }
    
    from engine import execute_workflow
    execute_workflow.__wrapped__("wf_2", def_dict)
    
    assert mock_execute_step.call_count == 0 # no steps executed due to cycle
    assert mock_update_wf.call_args_list[0][0][1] == WorkflowStatus.RUNNING
    assert mock_update_wf.call_args_list[1][0][1] == WorkflowStatus.FAILED

def test_execute_workflow_exception(mocker):
    mock_update_wf = mocker.patch("engine.update_workflow_status")
    mock_execute_step = mocker.patch("engine.execute_step", side_effect=ValueError("Execution Error"))
    
    def_dict = {
        "steps": [
            {"id": "A", "name": "A", "config": {"action": "x", "params": {}}, "depends_on": []},
        ]
    }
    
    from engine import execute_workflow
    with pytest.raises(ValueError):
        execute_workflow.__wrapped__("wf_3", def_dict)
        
    assert mock_update_wf.call_args_list[1][0][1] == WorkflowStatus.FAILED
