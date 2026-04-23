import subprocess
import os
import sqlite3
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, BackgroundTasks, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, List, Dict

from dotenv import load_dotenv
from database import init_db, update_job_status, DB_PATH
# from services.metashape_service import MetashapeService
# from core.enums import TaskType
# from core.pipelines import PIPELINE_PROFILES

from core.enums import EngineType
from engines.metashape.engine import MetashapeEngine
from engines.odm.engine import ODMEngine

REGISTERED_ENGINES = [MetashapeEngine, ODMEngine]

load_dotenv()

# --- WEBSOCKET MANAGER ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass # Handle disconnected clients

manager = ConnectionManager()

# --- APP LIFESPAN ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting up: Initializing Database...")
    init_db()
    yield
    print("Shutting down...")

class EndpointFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        return msg.find("/webhook/progress") == -1 and msg.find("/state") == -1

# Apply the filter immediately
logging.getLogger("uvicorn.access").addFilter(EndpointFilter())

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

OUTPUTS_DIR = os.path.abspath("../_outputs")
os.makedirs(OUTPUTS_DIR, exist_ok=True)
app.mount("/outputs", StaticFiles(directory=OUTPUTS_DIR), name="_outputs")

# --- DATA MODELS ---
class RunRequest(BaseModel):
    engine: str
    template: str = "FULL_PROCESS"
    profile: str

class WebhookPayload(BaseModel):
    job_id: int
    status: str
    step: str
    progress: float = 0.0

# --- MODULAR WORKER LAUNCHER ---
# --- MODULAR WORKER LAUNCHER ---
def run_modular_worker(job_id: int, dataset_name:str, input_path: str, output_path: str, config: RunRequest):
    try:
        # The universal worker script that knows how to initialize ANY engine
        worker_script = os.path.abspath(os.path.join(os.path.dirname(__file__), "core", "worker.py"))
        
        # We pass the pipeline config (including which engine to use) as a JSON string
        config_json = config.model_dump_json()

        # --- THE ENGINE ROUTER ---
        if config.engine == "metashape":
            # Metashape requires its own binary to run Python scripts
            metashape_bin = os.getenv("METASHAPE_BIN_PATH", r"C:\Program Files\Agisoft\Metashape Pro\metashape.exe")        
            cmd = [
                metashape_bin, 
                "-r", worker_script, 
                dataset_name, input_path, output_path, str(job_id), config_json
            ]
            
        # elif config.engine == "opendronemap":
        #     # Example: A pure Python engine just uses standard python
        #     python_bin = os.getenv("PYTHON_BIN", "python")
        #     cmd = [
        #         python_bin, worker_script, 
        #         dataset_name, input_path, output_path, str(job_id), config_json
        #     ]
            
        else:
            raise ValueError(f"Unsupported engine selected: {config.engine}")

        print(f"Starting {config.engine.upper()} Engine for Job {job_id}")
        
        # Launch the subprocess
        subprocess.run(cmd, check=True)
        
    except Exception as e:
        print(f"MODULAR ERROR: {e}")
        # Fallback error handling if the subprocess crashes entirely
        update_job_status(job_id, status="FAILED", step=str(e))

# --- WEBSOCKET ROUTE ---
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# --- WEBHOOK FOR METASHAPE WORKER ---
@app.post("/webhook/progress")
async def worker_webhook(payload: WebhookPayload):
    """
    The Metashape worker hits this URL to report its progress.
    We update the DB and broadcast via WebSockets.
    """
    # 1. Update Database
    update_job_status(payload.job_id, status=payload.status, step=payload.step, progress=payload.progress)
    
    # 2. Push to all frontend clients instantly
    await manager.broadcast(payload.model_dump())
    return {"received": True}


# --- UNIFIED WORKSPACE ENDPOINT ---
@app.get("/workspace")
async def get_workspace():
    """
    Returns available datasets AND their latest associated jobs in one package.
    """
    datasets_path = os.path.abspath("../_datasets")
    os.makedirs(datasets_path, exist_ok=True)
    
    # 1. Get all DB Jobs mapped by dataset name
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    # Get the latest job for each dataset
    cursor.execute("""
        SELECT * FROM jobs 
        WHERE id IN (
            SELECT MAX(id) FROM jobs GROUP BY dataset_name
        )
    """)
    jobs_data = {row["dataset_name"]: dict(row) for row in cursor.fetchall()}
    conn.close()

    # 2. Scan Datasets
    results = []
    valid_extensions = ('.jpg', '.jpeg', '.tif', '.tiff', '.png')

    for f in os.listdir(datasets_path):
        full_path = os.path.join(datasets_path, f)
        if os.path.isdir(full_path) and not f.startswith('.'):
            file_count = len([img for img in os.listdir(full_path) if img.lower().endswith(valid_extensions)])
            
            results.append({
                "dataset_name": f,
                "image_count": file_count,
                # Attach the job if it exists, otherwise None
                "latest_job": jobs_data.get(f) 
            })
            
    return results

# --- GRANULAR RUN ENDPOINT ---
@app.post("/run/{dataset_name}")
async def start_job(dataset_name: str, config: RunRequest, background_tasks: BackgroundTasks):
    input_path = os.path.abspath(f"../_datasets/{dataset_name}")
    output_path = os.path.abspath(f"../_outputs/{dataset_name}_out")
    
    if not os.path.exists(input_path):
        raise HTTPException(status_code=404, detail=f"Dataset not found.")
    
    # --- 1. VALIDATE THE ENGINE AND PROFILE ---
    # Find the matching engine class from our registry
    engine_class = next(
        (e for e in REGISTERED_ENGINES if e.get_info()["id"] == config.engine), 
        None
    )
    
    if not engine_class:
        raise HTTPException(status_code=400, detail=f"Engine '{config.engine}' is not registered.")

    # # Extract all valid profile IDs for this specific engine
    # valid_profile_ids = [p["id"] for p in engine_class.get_pipeline()]
    
    # # Block the request immediately if the profile string doesn't match
    # if config.profile not in valid_profile_ids:
    #     raise HTTPException(
    #         status_code=400, 
    #         detail=f"Invalid profile '{config.profile}' for engine '{config.engine}'. Valid options are: {valid_profile_ids}"
    #     )

    # 2. Database Record
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM jobs WHERE dataset_name = ?", (dataset_name,))
    cursor.execute(
        "INSERT INTO jobs (dataset_name, engine, profile, status, step) VALUES (?, ?, ?, ?, ?)", 
        (dataset_name, config.engine, config.profile, "PENDING", f"Queued...")
    )
    job_id = cursor.lastrowid
    conn.commit()
    conn.close()

    # 3. Notify frontend immediately
    await manager.broadcast({
        "job_id": job_id, "status": "PENDING", "step": "Queued", "progress": 0.0
    })

    # 4. Start Worker
    background_tasks.add_task(run_modular_worker, job_id, dataset_name, input_path, output_path, config)
    
    return {"message": "Pipeline initiated", "job_id": job_id}


# @app.get("/state/{dataset_name}")
# async def get_dataset_state(dataset_name: str):
#     try:
#         service = MetashapeService(dataset_name)
#         steps = service.get_completed_steps()
#         return {"completed_steps": steps}

#     except Exception as e:
#         print(f"Error reading PSX: {e}")
#         # If the file is corrupted or unreadable, return empty
#         return {"completed_steps": []}
    

import asyncio
import json

# --- STATE WEBSOCKET (Watches tasks.json) ---
@app.websocket("/api/ws/state/{dataset_name}")
async def websocket_state_endpoint(websocket: WebSocket, dataset_name: str):
    await websocket.accept()
    
    # Calculate the exact path to where MetashapeService saves the tasks.json
    # Matches your MetashapeService: f"../_outputs/{dataset_name}_out"
    output_path = os.path.join(OUTPUTS_DIR, f"{dataset_name}_out")
    state_file_path = os.path.join(output_path, "tasks.json")
    
    last_mtime = 0
    
    try:
        while True:
            if os.path.exists(state_file_path):
                current_mtime = os.path.getmtime(state_file_path)
                
                # If the file was modified since we last checked
                if current_mtime != last_mtime:
                    try:
                        with open(state_file_path, "r") as f:
                            state_data = json.load(f)
                        
                        await websocket.send_json(state_data)
                        last_mtime = current_mtime
                    except json.JSONDecodeError:
                        pass # Ignore temporary read errors while file is being written
            else:
                # If file doesn't exist yet, send empty state once
                if last_mtime != -1:
                    await websocket.send_json({"completed_steps": []})
                    last_mtime = -1
            
            # Check every 1 second
            await asyncio.sleep(1.0)
            
    except WebSocketDisconnect:
        print(f"[WS] Client stopped watching state for {dataset_name}")

# @app.get("/pipelines")
# async def get_pipelines():
#     return PIPELINE_PROFILES

@app.get("/engines")
async def get_available_engines():
    """
    Returns all registered engines AND their available pipelines 
    in a single, nested JSON payload for the frontend UI.
    """
    payload = []
    
    for engine_class in REGISTERED_ENGINES:
        # Get the base info (id, name, description)
        engine_data = engine_class.get_info()
        payload.append(engine_data)
        
    return payload

if __name__ == "__main__":
    import uvicorn

    # Start the server
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)