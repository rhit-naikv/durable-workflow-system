# Durable Workflow Execution System

A full-stack system that accepts JSON workflow definitions (DAGs), executes them durably with crash recovery, and provides a real-time visualization UI.

## Quick Start

```bash
# Clone and start all services (PostgreSQL, Backend, Frontend)
docker compose up --build
```

| Service    | URL                        |
|------------|----------------------------|
| Frontend   | http://localhost:5173       |
| Backend    | http://localhost:8000       |
| Health     | http://localhost:8000/api/health |

> **Requirements:** Docker and Docker Compose.

## Architecture

```
┌───────────────────────┐     REST / Polling     ┌──────────────────────────────┐
│   React + Vite SPA    │ ◄──────────────────────►│   FastAPI + DBOS Transact    │
│   (Tailwind CSS)      │                         │   (Python 3.11)              │
│                       │                         │                              │
│  • Submit JSON DAG    │                         │  • @DBOS.workflow() — DAG    │
│  • Dashboard (list)   │                         │    resolution via Kahn's     │
│  • Timeline Detail    │                         │    algorithm                 │
│  • 1s status polling  │                         │  • @DBOS.step() — durable    │
└───────────────────────┘                         │    task checkpointing        │
                                                  └────────────┬─────────────────┘
                                                               │
                                                  ┌────────────▼─────────────────┐
                                                  │      PostgreSQL 15           │
                                                  │                              │
                                                  │  • Application state         │
                                                  │    (workflows, step_execs)   │
                                                  │  • DBOS internal state       │
                                                  │    (transaction log, replay) │
                                                  └──────────────────────────────┘
```

**How durability works:** DBOS Transact wraps each step execution in a PostgreSQL transaction. If the server is killed mid-workflow (`SIGKILL`), DBOS's deterministic replay mechanism automatically resumes the workflow on restart — skipping already-completed steps using cached results from the transaction log. No duplicate work occurs.

## Workflow JSON Format

```json
{
  "name": "order-processing",
  "steps": [
    {
      "id": "validate",
      "type": "task",
      "config": {
        "action": "validate_order"
      },
      "depends_on": []
    }
  ]
}
```

| Field | Required | Description |
|---|---|---|
| `name` | Yes | Human-readable workflow name |
| `steps[].id` | Yes | Unique step identifier |
| `steps[].type` | No | Step classification (default: `"task"`) |
| `steps[].config.action` | Yes | Action to execute (e.g., `fetch_dataset`, `call_llm`) |
| `steps[].config.params` | No | Arbitrary parameters passed to the action handler |
| `steps[].depends_on` | No | List of step IDs that must complete first (default: `[]`) |

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/workflows` | Submit a JSON DAG and start execution |
| `GET` | `/api/workflows` | List all workflow runs with progress |
| `GET` | `/api/workflows/{id}/state` | Full state of a run (step statuses, payloads, timing) |
| `GET` | `/api/health` | Health check |

## Testing Crash Recovery

```bash
# 1. Submit a workflow via the UI at http://localhost:5173/submit

# 2. While it's running, kill the backend
docker compose kill -s SIGKILL backend

# 3. Restart the backend
docker compose up backend -d

# 4. Refresh the UI — the workflow resumes from where it left off
```

## Key Decisions

See [DECISIONS.md](./DECISIONS.md) for detailed evaluation of alternatives (Temporal, Celery/BullMQ, custom state machine) and rationale for choosing DBOS Transact, Python, and REST polling.

**Summary:**
- **DBOS Transact** over Temporal/Celery — exactly-once semantics without operational overhead
- **Python** — native integration with AI/ML ecosystem (LangChain, Ollama)
- **REST short-polling** over WebSockets — resilient to server crashes, no reconnect logic needed
- **Timeline UI** over 2D node-graph — prioritizes functional clarity for V1

## Project Structure

```
├── backend/
│   ├── main.py          # FastAPI app + DBOS setup + API endpoints
│   ├── engine.py        # @DBOS.workflow DAG resolver + @DBOS.step executor
│   ├── database.py      # PostgreSQL state store (pooled connections)
│   ├── models.py        # Pydantic input/output schemas
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.tsx              # Router + navigation shell
│   │   ├── api.ts               # Typed API client
│   │   ├── pages/
│   │   │   ├── DashboardPage.tsx # Run history table
│   │   │   ├── SubmitPage.tsx    # JSON editor + submit
│   │   │   └── RunDetailPage.tsx # Timeline visualization
│   │   └── components/
│   │       └── StatusBadge.tsx   # Color-coded status indicators
│   └── Dockerfile
├── docker-compose.yml
├── DECISIONS.md
└── DESIGN_DOC.md
```

## Limitations

- **Sequential tier execution**: Steps within the same dependency tier run sequentially (V2 would use `asyncio.gather()` or distributed workers)
- **Polling latency**: UI updates are delayed by up to 1 second
- **Single-node execution**: No distributed worker pool — all steps run on the API server

See [DECISIONS.md §2](./DECISIONS.md#2-limitations--future-work) for the full discussion.
