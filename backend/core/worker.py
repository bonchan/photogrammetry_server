import sys
from pathlib import Path
import math

# --- BOOTSTRAP: Add project root to sys.path ---
# This script is at: project_root/core/worker.py
# We need to add: project_root
current_file = Path(__file__).resolve()
project_root = current_file.parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))
# -----------------------------------------------

# NOW you can import your modules
import os
import json
import urllib.request
from core.enums import EngineType
from engines.factory import get_engine

class SmartWorker:
    def __init__(self, engine, job_id: str):
        self.engine = engine
        self.job_id = job_id
        
        # Hardcoded to your FastAPI webhook (or passed via env vars later)
        self.webhook_url = "http://127.0.0.1:8000/webhook/progress" 
        self.current_task_name = "Initializing"
        self.last_progress_sent = -1.0

    def set_current_task(self, task_name: str):
        self.current_task_name = task_name
        self.last_progress_sent = -1.0
        self._send_webhook("PROCESSING", 0.0)

    def log(self, message): 
        print(f"[LOG] {message}")
        self._send_webhook("PROCESSING", progress=None, message=message)

    def progress_callback(self, p: float):
        """
        We will pass this function to the Engine so the engine 
        can report C++ processing progress back to the UI.
        """
        print(f"      Progress: {p:.1f}%", end="\r")
        if (p - self.last_progress_sent >= 1.0) or (p >= 100.0):
            self._send_webhook("PROCESSING", progress=p)
            self.last_progress_sent = p

    def _send_webhook(self, status: str, progress: float = None, message: str = ""):
        task_text = self.current_task_name
        if message:
            task_text = f"{self.current_task_name}: {message[:50]}..." 

        payload = {
            "job_id": self.job_id,
            "status": status,
            "step": task_text
        }
        if progress is not None:
            payload["progress"] = round(progress, 1)

        try:
            req = urllib.request.Request(
                self.webhook_url,
                data=json.dumps(payload).encode('utf-8'),
                headers={'Content-Type': 'application/json'}
            )
            urllib.request.urlopen(req, timeout=1.0)
        except Exception:
            pass # Fail silently so photogrammetry doesn't stop if UI drops

def run_job(dataset_name, input_dir, output_dir, job_id, config):
    print(f"[DEBUG] Incoming config payload: {config}")
    
    # 1. Ask the Factory for the right engine
    engine_name = config.get("engine", "metashape")
    engine = get_engine(engine_name, dataset_name, input_dir, output_dir)
    
    worker = SmartWorker(engine, job_id)
    
    # 2. Extract Intent
    profile_name = config.get("profile")
    template_name = config.get("template", "FULL_PROCESS")
    
    pipeline_tasks = engine.get_pipeline(profile_name)
    template_params = engine.get_template(template_name)

    if not pipeline_tasks:
        worker.log(f"Mission Failed: Profile '{profile_name}' not found for engine {engine_name}.")
        worker._send_webhook("FAILED", 0.0)
        return

    # 3. Init Engine & Calculate Delta
    worker.engine.load_project(read_only=False)
    completed_tasks = worker.engine.get_completed_tasks()
    
    tasks_to_run = [task for task in pipeline_tasks if task not in completed_tasks]
    worker.log(f"Mission: {profile_name} | Tasks to execute: {tasks_to_run}")

    # 4. Dynamic Execution Loop
    try:
        for task_type in tasks_to_run:
            worker.set_current_task(task_type)
            
            # Fetch params and inject the progress callback!
            params = template_params.get(task_type, {})
            params["progress_cb"] = worker.progress_callback 
            
            print(f'Running task {task_type} with params: {params}')
            
            # The Worker doesn't know HOW it happens, it just tells the Engine to do it
            success = worker.engine.execute_task(task_type, params)
            
            if success:
                worker.engine.save_project()
                worker.engine.sync_state_file()
                print(f"<< COMPLETED: {task_type}\n")
                worker._send_webhook("MILESTONE_COMPLETED", progress=100.0, message=str(task_type))
            else:
                worker.log(f"FAILED: {task_type}")
                worker._send_webhook("FAILED", 0.0, f"Task {task_type} failed in {engine_name} engine.")
                break

        # Notice how the massive "Export" loop is gone! 
        # Exporting is just another task (like MetashapeTask.EXPORT) handled in the loop above.
        
        # If we finished the loop successfully and didn't break out:
        if success:
            worker._send_webhook("COMPLETED", 100.0, "Mission Accomplished")

    except Exception as e:
        print(f"\nFATAL ERROR: {str(e)}")
        worker._send_webhook("FAILED", 0.0, str(e))

if __name__ == "__main__":
    # If run by FastAPI subprocess
    DATASET_NAME = sys.argv[1]
    INPUT_DIR = sys.argv[2]
    OUTPUT_DIR = sys.argv[3]
    JOB_ID = int(sys.argv[4])
    
    try:
        CONFIG = json.loads(sys.argv[5])
    except json.JSONDecodeError:
        print("Failed to decode JSON config.")
        CONFIG = {}

    run_job(DATASET_NAME, INPUT_DIR, OUTPUT_DIR, JOB_ID, CONFIG)