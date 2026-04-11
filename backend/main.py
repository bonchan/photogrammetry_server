import subprocess
import os
from dotenv import load_dotenv
import sqlite3
import shutil
from contextlib import asynccontextmanager
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Use absolute imports if running from the root folder
from backend.database import init_db, update_job_status, DB_PATH

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting up: Initializing Database...")
    init_db()
    yield
    print("Shutting down...")

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

OUTPUTS_DIR = os.path.abspath("./_outputs")

if not os.path.exists(OUTPUTS_DIR):
    os.makedirs(OUTPUTS_DIR)

app.mount("/outputs", StaticFiles(directory=OUTPUTS_DIR), name="_outputs")


# --- WORKER FUNCTION ---
def run_metashape_headless(job_id: int, image_folder: str, output_folder: str):
    try:
        update_job_status(job_id, status="PROCESSING", step="Launching Metashape Engine")
        
        # 1. Define the path (Windows style for subprocess)
        metashape_bin = os.getenv("METASHAPE_BIN_PATH", r"C:\Program Files\Agisoft\Metashape Pro\metashape.exe")        
        # 2. Path to your worker script
        worker_script = os.path.abspath(os.path.join(os.path.dirname(__file__), "worker.py"))
        
        # 3. Build the command
        # -r tells Metashape to run the script and exit
        cmd = [
            metashape_bin, 
            "-r", 
            worker_script, 
            image_folder, 
            output_folder, 
            str(job_id)
        ]
        
        print(f"Starting Metashape: {' '.join(cmd)}")
        
        # Run the command
        subprocess.run(cmd, check=True)
        
        update_job_status(job_id, status="COMPLETED", progress=100.0, step="Done")
        
    except Exception as e:
        print(f"METASHAPE ERROR: {e}")
        update_job_status(job_id, status="FAILED", step=str(e))

# --- ROUTES ---

@app.get("/available-datasets")
async def list_available_datasets():
    datasets_path = os.path.abspath("./_datasets")
    
    if not os.path.exists(datasets_path):
        os.makedirs(datasets_path)
        return []

    results = []
    # Common image extensions to look for
    valid_extensions = ('.jpg', '.jpeg', '.tif', '.tiff', '.png')

    for f in os.listdir(datasets_path):
        full_path = os.path.join(datasets_path, f)

        if os.path.isdir(full_path) and not f.startswith('.'):
            # Count the files inside this specific folder
            file_count = len([
                img for img in os.listdir(full_path) 
                if img.lower().endswith(valid_extensions)
            ])
            
            results.append({
                "name": f,
                "count": file_count
            })
            
    return results

@app.get("/jobs")
async def list_jobs():
    """Returns all jobs from the SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row # This makes it return dictionaries
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM jobs ORDER BY updated_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

@app.post("/run/{dataset_name}")
async def start_job(dataset_name: str, background_tasks: BackgroundTasks):
    image_path = os.path.abspath(f"./_datasets/{dataset_name}")
    output_path = os.path.abspath(f"./_outputs/{dataset_name}_out")
    
    if not os.path.exists(image_path):
        raise HTTPException(status_code=404, detail=f"Folder not found in datasets: {dataset_name}")

    # --- 1. Clean up old output folder ---
    if os.path.exists(output_path):
        shutil.rmtree(output_path)  # Recursively deletes the folder and all heavy files
    os.makedirs(output_path, exist_ok=True)  # Create a fresh empty folder

    # --- 2. Clean up old DB records & Insert new one ---
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Nuke the old job history for this dataset
    cursor.execute("DELETE FROM jobs WHERE dataset_name = ?", (dataset_name,))
    
    # Insert the fresh job
    cursor.execute(
        "INSERT INTO jobs (dataset_name, status, step) VALUES (?, ?, ?)", 
        (dataset_name, "PENDING", "Queued")
    )
    job_id = cursor.lastrowid
    conn.commit()
    conn.close()

    # --- 3. Start the background process ---
    background_tasks.add_task(run_metashape_headless, job_id, image_path, output_path)
    
    return {"message": "Job started", "job_id": job_id}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)