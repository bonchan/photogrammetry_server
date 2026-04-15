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
from services.metashape_service import MetashapeService
from core.enums import TaskType
from core.pipelines import PIPELINE_PROFILES


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
    template: str = "FULL_PROCESS"
    profile: str


class WebhookPayload(BaseModel):
    job_id: int
    status: str
    step: str
    progress: float = 0.0

# --- MODULAR WORKER LAUNCHER ---
def run_modular_worker(job_id: int, dataset_name:str, image_folder: str, output_folder: str, config: RunRequest):
    try:
        metashape_bin = os.getenv("METASHAPE_BIN_PATH", r"C:\Program Files\Agisoft\Metashape Pro\metashape.exe")        
        worker_script = os.path.abspath(os.path.join(os.path.dirname(__file__), "smart_worker.py"))
        
        # We pass the pipeline config as a JSON string to the CLI
        config_json = config.model_dump_json()

        cmd = [
            metashape_bin, 
            "-r", worker_script, 
            dataset_name,
            image_folder, 
            output_folder, 
            str(job_id),
            config_json
        ]
        
        print(f"Starting Modular Engine for Job {job_id}")
        subprocess.run(cmd, check=True)
        
    except Exception as e:
        print(f"MODULAR ERROR: {e}")
        # Fallback error handling if the subprocess crashes entirely
        update_job_status(job_id, status="FAILED", step=str(e))
        # Note: In reality, we'd want to trigger a WS broadcast here too, 
        # but usually the webhook handles normal errors.

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
    image_path = os.path.abspath(f"../_datasets/{dataset_name}")
    output_path = os.path.abspath(f"../_outputs/{dataset_name}_out")
    
    if not os.path.exists(image_path):
        raise HTTPException(status_code=404, detail=f"Dataset not found.")

    # 2. Database Record
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM jobs WHERE dataset_name = ?", (dataset_name,))
    cursor.execute(
        "INSERT INTO jobs (dataset_name, status, step) VALUES (?, ?, ?)", 
        (dataset_name, "PENDING", f"Queued (From: {'Start'})")
    )
    job_id = cursor.lastrowid
    conn.commit()
    conn.close()

    # 3. Notify frontend immediately
    await manager.broadcast({
        "job_id": job_id, "status": "PENDING", "step": "Queued", "progress": 0.0
    })

    # 4. Start Worker
    background_tasks.add_task(run_modular_worker, job_id, dataset_name, image_path, output_path, config)
    
    return {"message": "Pipeline initiated", "job_id": job_id}


@app.get("/state/{dataset_name}")
async def get_dataset_state(dataset_name: str):
    try:
        service = MetashapeService(dataset_name)
        steps = service.get_completed_steps()
        return {"completed_steps": steps}

    except Exception as e:
        print(f"Error reading PSX: {e}")
        # If the file is corrupted or unreadable, return empty
        return {"completed_steps": []}

@app.get("/pipelines")
async def get_pipelines():
    return PIPELINE_PROFILES


if __name__ == "__main__":
    import uvicorn

    # Start the server
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)