import pytest
from datetime import datetime
from fastapi.testclient import TestClient

@pytest.fixture
def client(mocker):
    mocker.patch("main.init_db")
    # Patch DBOS launch to avoid DB connections during TestClient lifespan execution
    mocker.patch("dbos.DBOS._launch")
    mocker.patch("dbos.DBOS.destroy", create=True)
    mocker.patch("main.DBOS.start_workflow")
    from main import app
    with TestClient(app) as c:
        yield c

def test_health_check(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "online"

def test_submit_workflow_success(client, mocker):
    mocker.patch("main.create_workflow_run", return_value="fake-uuid-123")
    data = {
        "name": "Test Workflow",
        "steps": [
            {
                "id": "A",
                "config": {"action": "validate_order"},
                "depends_on": []
            }
        ]
    }
    response = client.post("/api/workflows", json=data)
    assert response.status_code == 200
    assert response.json() == {"workflow_id": "fake-uuid-123"}

def test_submit_workflow_missing_name(client):
    data = {
        "steps": [
            {
                "id": "A",
                "config": {"action": "validate_order"},
                "depends_on": []
            }
        ]
    }
    response = client.post("/api/workflows", json=data)
    assert response.status_code == 422

def test_submit_workflow_cycle_rejected(client):
    data = {
        "name": "Cycle",
        "steps": [
            {"id": "A", "config": {"action": "val"}, "depends_on": ["B"]},
            {"id": "B", "config": {"action": "val"}, "depends_on": ["A"]},
        ]
    }
    response = client.post("/api/workflows", json=data)
    assert response.status_code == 422
    assert "cyclic" in response.text.lower()

def test_submit_workflow_duplicate_ids(client):
    data = {
        "name": "Dupes",
        "steps": [
            {"id": "A", "config": {"action": "val"}, "depends_on": []},
            {"id": "A", "config": {"action": "val"}, "depends_on": []},
        ]
    }
    response = client.post("/api/workflows", json=data)
    assert response.status_code == 422
    assert "duplicate" in response.text.lower()

def test_submit_workflow_bad_depends_on(client):
    data = {
        "name": "Bad Dep",
        "steps": [
            {"id": "A", "config": {"action": "val"}, "depends_on": ["Unknown"]},
        ]
    }
    response = client.post("/api/workflows", json=data)
    assert response.status_code == 422
    assert "unknown" in response.text.lower()

def test_list_workflows_empty(client, mocker):
    mocker.patch("main.list_workflow_runs", return_value=[])
    response = client.get("/api/workflows")
    assert response.status_code == 200
    assert response.json() == []

def test_list_workflows_returns_data(client, mocker):
    now = datetime.fromtimestamp(1000000000).isoformat()
    mock_data = [
        {
            "workflow_id": "test-uuid-1",
            "name": "Flow 1",
            "status": "PENDING",
            "created_at": now,
            "completed_at": None,
            "total_steps": 5,
            "completed_steps": 2,
        }
    ]
    mocker.patch("main.list_workflow_runs", return_value=mock_data)
    response = client.get("/api/workflows")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["workflow_id"] == "test-uuid-1"
    assert response.json()[0]["total_steps"] == 5

def test_get_state_invalid_uuid(client):
    # Pass malformed UUID
    response = client.get("/api/workflows/invalid-uuid-string/state")
    assert response.status_code == 404

def test_get_state_not_found(client, mocker):
    # Pass valid UUID but DB returns None
    mocker.patch("main.get_workflow_state", return_value=None)
    response = client.get("/api/workflows/12345678-1234-5678-1234-567812345678/state")
    assert response.status_code == 404

def test_get_state_success(client, mocker):
    now = datetime.fromtimestamp(1000000000).isoformat()
    mock_state = {
        "workflow_id": "12345678-1234-5678-1234-567812345678",
        "name": "Flow 1",
        "status": "PENDING",
        "created_at": now,
        "completed_at": None,
        "steps": [
            {
                "step_id": "A",
                "step_name": "A",
                "status": "COMPLETED",
                "action": "test",
                "depends_on": [],
                "result_payload": {"ok": True},
                "started_at": now,
                "completed_at": now,
            }
        ]
    }
    mocker.patch("main.get_workflow_state", return_value=mock_state)
    response = client.get("/api/workflows/12345678-1234-5678-1234-567812345678/state")
    assert response.status_code == 200
    data = response.json()
    assert data["workflow_id"] == "12345678-1234-5678-1234-567812345678"
    assert len(data["steps"]) == 1
    assert data["steps"][0]["step_id"] == "A"
