import sys
import os
import zipfile
import json
import urllib.request
from urllib.error import URLError

# Get the directory where worker.py lives (which is the backend folder)
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

import Metashape # type: ignore
from core.enums import TaskType
from tasks import TASK_REGISTRY

from services.metashape_service import MetashapeService
from core.pipelines import PIPELINE_PROFILES
from core.templates import PIPELINE_TEMPLATES

class SmartWorker:
    def __init__(self, image_folder, output_folder, job_id):
        self.image_folder = image_folder
        self.output_folder = output_folder
        self.job_id = job_id
        self.interrupted = False
        # Hardcoded to your FastAPI webhook
        self.webhook_url = "http://127.0.0.1:8000/webhook/progress" 
        self.current_task_name = "Initializing"

        self.last_progress_sent = -1.0

    def set_current_task(self, task_name: str):
        """Called right before a new task starts."""
        self.current_task_name = task_name
        self.last_progress_sent = -1.0
        self._send_webhook("PROCESSING", 0.0)

    def log(self, message): 
        """Logs to terminal and updates the UI step description."""
        print(f"[LOG] {message}")
        self._send_webhook("PROCESSING", progress=None, message=message)

    def progress_callback(self, p):
        """Called repeatedly by Metashape's internal C++ engine."""
        print(f"      Progress: {p:.1f}%", end="\r")
        if (p - self.last_progress_sent >= 1.0) or (p >= 100.0):
            self._send_webhook("PROCESSING", progress=p)
            self.last_progress_sent = p

    def _send_webhook(self, status: str, progress: float = None, message: str = ""):
        """Pushes updates to FastAPI without needing external libraries like 'requests'."""
        step_text = self.current_task_name
        if message:
            step_text = f"{self.current_task_name}: {message[:50]}..." 

        payload = {
            "job_id": self.job_id,
            "status": status,
            "step": step_text
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

def run_dynamic_pipeline(dataset_name, image_dir, output_dir, job_id, config):
    worker = SmartWorker(image_dir, output_dir, job_id)

    print(f"[DEBUG] Incoming config payload: {config}")
    
    template_name = config.get("template", "FULL_PROCESS")
    profile_name = config.get("profile")
    
    if not profile_name or profile_name not in PIPELINE_PROFILES:
        worker.log(f"Mission Failed: Profile '{profile_name}' not found.")
        worker._send_webhook("FAILED", 0.0, f"Mission Failed: Profile '{profile_name}' not found.")
        return

    # 1. INIT SERVICE & LOAD PROJECT (Write Mode)
    service = MetashapeService(dataset_name)
    service.load_project(read_only=False) # Opens or creates the .psx once!
    
    worker.chunk = service.chunk 

    # 2. CALCULATE DELTA
    completed_steps = service.get_completed_steps() # Uses the already-open doc
    pipeline_tasks = PIPELINE_PROFILES[profile_name]["tasks"]

    selected_template = PIPELINE_TEMPLATES.get(template_name, {})

    template_params = selected_template.get("params", {})
    
    tasks_to_run = [task for task in pipeline_tasks if task not in completed_steps]
    worker.log(f"Mission: {profile_name} | Tasks to execute: {[t for t in tasks_to_run]}")

    # 3. DYNAMIC EXECUTION LOOP
    try:
        for task_type in tasks_to_run:
            worker.set_current_task(task_type)
            
            task_class = TASK_REGISTRY.get(task_type)
            params = template_params.get(task_type, {})
            task_instance = task_class(worker)
            
            if not task_instance.validate_dependencies():
                worker.log(f"Dependencies failed for {task_type}")
                worker._send_webhook("FAILED", 0.0, f"Dependencies failed for {task_type}")
                break

            print(f'running task with params: {params}')
            success = task_instance.run(params)
            
            if success:
                service.save_project() # Clean, single-line save
                print(f"<< COMPLETED: {task_type}")
                worker._send_webhook("MILESTONE_COMPLETED", progress=100.0, message=task_type.value)
            else:
                worker.log(f"FAILED: {task_type}")
                worker._send_webhook("FAILED", 0.0, f"FAILED: {task_type}")
                break

        # 4. EXPORT LOOP
        worker.set_current_task("Exporting Deliverables")
        os.makedirs(service.export_path, exist_ok=True)
        
        export_status = service.get_export_status()
        expected = service.expected_files
        chunk = service.chunk # Local reference for brevity

        if chunk.orthomosaic and not export_status.get("ortho"):
            worker.log("Exporting Orthomosaic...")
            chunk.exportRaster(path=os.path.join(service.export_path, expected["ortho"]), source_data=Metashape.OrthomosaicData)

        # ... (other exports: DEM, Model, Point Cloud exactly as before) ...

        worker._send_webhook("COMPLETED", 100.0, "Mission Accomplished")

    except Exception as e:
        print(f"\nFATAL ERROR: {str(e)}")
        worker._send_webhook("FAILED", 0.0, str(e))

if __name__ == "__main__":
    # If run by FastAPI subprocess
    DATASET_NAME = sys.argv[1]
    IMAGE_DIR = sys.argv[2]
    OUTPUT_DIR = sys.argv[3]
    JOB_ID = int(sys.argv[4])
    
    try:
        CONFIG = json.loads(sys.argv[5])
    except json.JSONDecodeError:
        print("Failed to decode JSON config.")
        CONFIG = {}

    run_dynamic_pipeline(DATASET_NAME, IMAGE_DIR, OUTPUT_DIR, JOB_ID, CONFIG)