import pytest
import json
from datetime import datetime
from database import (
    get_connection_string,
    get_pool,
    init_db,
    create_workflow_run,
    list_workflow_runs,
    get_workflow_state,
    update_step_status,
    update_workflow_status
)
from models import StepStatus, WorkflowStatus

def test_get_connection_string_default(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert get_connection_string() == "postgresql://postgres:dbos_password@postgres:5432/workflow_db"

def test_get_connection_string_custom(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "test_url")
    assert get_connection_string() == "test_url"

def test_get_pool_singleton():
    # Calling twice should return same pool
    p1 = get_pool()
    p2 = get_pool()
    assert p1 is p2

def test_init_db(mocker):
    # Mock pool and connection
    mock_pool = mocker.patch("database.get_pool")
    mock_conn = mock_pool.return_value.connection.return_value.__enter__.return_value
    mock_cur = mock_conn.cursor.return_value.__enter__.return_value

    init_db()

    assert mock_cur.execute.call_count == 3
    mock_conn.commit.assert_called_once()

def test_create_workflow_run(mocker):
    mock_pool = mocker.patch("database.get_pool")
    mock_conn = mock_pool.return_value.connection.return_value.__enter__.return_value
    mock_cur = mock_conn.cursor.return_value.__enter__.return_value
    
    steps = [
        {"id": "A", "name": "Step A", "config": {"action": "action_a"}, "depends_on": []}
    ]
    def_dict = {"name": "WF", "steps": steps}
    
    wf_id = create_workflow_run("WF", def_dict, steps)
    
    assert isinstance(wf_id, str)
    assert mock_cur.execute.call_count == 2 # 1 workflow + 1 step
    mock_conn.commit.assert_called_once()
    
    # Check workflow insert
    wf_args = mock_cur.execute.call_args_list[0][0]
    assert "INSERT INTO workflows" in wf_args[0]
    assert wf_args[1][1] == "WF"
    
    # Check step insert
    step_args = mock_cur.execute.call_args_list[1][0]
    assert "INSERT INTO step_executions" in step_args[0]
    assert step_args[1][1] == wf_id
    assert step_args[1][3] == "Step A"
    assert step_args[1][4] == "action_a"

def test_list_workflow_runs(mocker):
    mock_pool = mocker.patch("database.get_pool")
    mock_conn = mock_pool.return_value.connection.return_value.__enter__.return_value
    mock_cur = mock_conn.cursor.return_value.__enter__.return_value
    
    mock_cur.fetchall.return_value = [{"workflow_id": "123", "name": "Test"}]
    
    res = list_workflow_runs()
    
    assert res == [{"workflow_id": "123", "name": "Test"}]
    assert mock_cur.execute.call_count == 1
    assert "SELECT" in mock_cur.execute.call_args[0][0]

def test_get_workflow_state_not_found(mocker):
    mock_pool = mocker.patch("database.get_pool")
    mock_conn = mock_pool.return_value.connection.return_value.__enter__.return_value
    mock_cur = mock_conn.cursor.return_value.__enter__.return_value
    
    mock_cur.fetchone.return_value = None
    
    assert get_workflow_state("missing") is None

def test_get_workflow_state_found(mocker):
    mock_pool = mocker.patch("database.get_pool")
    mock_conn = mock_pool.return_value.connection.return_value.__enter__.return_value
    mock_cur = mock_conn.cursor.return_value.__enter__.return_value
    
    mock_cur.fetchone.return_value = {"workflow_id": "123", "name": "WF"}
    mock_cur.fetchall.return_value = [{"step_id": "A", "action": "test"}]
    
    res = get_workflow_state("123")
    assert res["name"] == "WF"
    assert len(res["steps"]) == 1

def test_update_step_status_running(mocker):
    mock_pool = mocker.patch("database.get_pool")
    mock_conn = mock_pool.return_value.connection.return_value.__enter__.return_value
    mock_cur = mock_conn.cursor.return_value.__enter__.return_value
    
    update_step_status("wf_id", "step_A", StepStatus.RUNNING)
    
    mock_conn.commit.assert_called_once()
    args = mock_cur.execute.call_args[0]
    assert "started_at" in args[0]
    assert args[1][0] == StepStatus.RUNNING

def test_update_step_status_completed(mocker):
    mock_pool = mocker.patch("database.get_pool")
    mock_conn = mock_pool.return_value.connection.return_value.__enter__.return_value
    mock_cur = mock_conn.cursor.return_value.__enter__.return_value
    
    update_step_status("w_id", "s_id", StepStatus.COMPLETED, result_payload={"a": 1})
    
    mock_conn.commit.assert_called_once()
    args = mock_cur.execute.call_args[0]
    assert "completed_at" in args[0]
    assert "result_payload" in args[0]
    assert json.loads(args[1][2]) == {"a": 1}

def test_update_step_status_pending(mocker):
    mock_pool = mocker.patch("database.get_pool")
    mock_conn = mock_pool.return_value.connection.return_value.__enter__.return_value
    mock_cur = mock_conn.cursor.return_value.__enter__.return_value
    
    update_step_status("w_id", "s_id", StepStatus.PENDING)
    
    mock_conn.commit.assert_called_once()
    args = mock_cur.execute.call_args[0]
    assert "started_at" not in args[0] # Just regular status update
    assert args[1][0] == StepStatus.PENDING

def test_update_workflow_status_completed(mocker):
    mock_pool = mocker.patch("database.get_pool")
    mock_conn = mock_pool.return_value.connection.return_value.__enter__.return_value
    mock_cur = mock_conn.cursor.return_value.__enter__.return_value
    
    update_workflow_status("w_id", WorkflowStatus.COMPLETED)
    
    mock_conn.commit.assert_called_once()
    args = mock_cur.execute.call_args[0]
    assert "completed_at =" in args[0]

def test_update_workflow_status_running(mocker):
    mock_pool = mocker.patch("database.get_pool")
    mock_conn = mock_pool.return_value.connection.return_value.__enter__.return_value
    mock_cur = mock_conn.cursor.return_value.__enter__.return_value
    
    update_workflow_status("w_id", WorkflowStatus.RUNNING)
    
    mock_conn.commit.assert_called_once()
    args = mock_cur.execute.call_args[0]
    assert "completed_at" not in args[0]
