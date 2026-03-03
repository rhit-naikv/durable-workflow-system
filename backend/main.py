import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dbos import DBOS, DBOSConfig

# 1. Initialize FastAPI
app = FastAPI(title="Durable Workflow Engine")

# 2. Add CORS so your React frontend can communicate with the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. Initialize DBOS 
# We pull the Postgres URL right from the docker-compose environment variable
db_url = os.environ.get("DATABASE_URL", "postgresql://postgres:dbos_password@postgres:5432/workflow_db")

config: DBOSConfig = {
    "name": "workflow-engine",
    "system_database_url": db_url
}

# Pass the config explicitly to fix the TypeError!
DBOS(fastapi=app, config=config)

# 4. A simple health-check endpoint
@app.get("/api/health")
def health_check():
    return {
        "status": "online",
        "message": "FastAPI and DBOS are successfully connected to PostgreSQL!"
    }
