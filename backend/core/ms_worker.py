import os
import Metashape  # type: ignore
from core.base_worker import BaseWorker
from core.enums import JobStatus, StepStatus, TaskType
from database import update_job_status, get_job_config
from tasks import TASK_REGISTRY

class MetashapeWorker(BaseWorker):
    def __init__(self, job_id: int, image_folder: str, output_folder: str):
        super().__init__(job_id)
        self.image_folder = image_folder
        self.output_folder = output_folder
        self.doc = Metashape.Document()
        self.chunk = None
        self.current_step = None
        
        # Tracks states
        self.steps_state = {} 

    def on_shutdown(self):
        """Emergency save on SIGINT/SIGTERM"""
        if self.doc and self.chunk:
            try:
                self.doc.save()
                print(f"[Worker {self.job_id}] Project saved during shutdown.")
            except Exception as e:
                print(f"Failed to save project: {e}")

    def run(self):
        try:
            # 1. Setup
            config = get_job_config(self.job_id)
            pipeline = config.get("pipeline", [])
            
            self.update_progress(step="Initializing", progress=0)
            update_job_status(self.job_id, status=JobStatus.PROCESSING)
            
            self._load_or_create_project()

            # 2. Iterate through requested steps
            for step_key in pipeline:
                if self.interrupted:
                    break
                
                self.current_step = step_key
                task_class = TASK_REGISTRY.get(step_key)
                
                if not task_class:
                    print(f"Warning: Task {step_key} not found in registry.")
                    continue

                # Initialize task instance
                task = task_class(self)

                # 3. Dependency & Checkpoint Check
                # If step is done and params haven't changed, we could skip. 
                # For now, we assume if it's in the pipeline, we run it.
                
                if not task.validate_dependencies():
                    self.update_step_state(step_key, StepStatus.FAILED)
                    raise Exception(f"Dependencies failed for step: {step_key}")

                # 4. Execute Task
                self.update_step_state(step_key, StepStatus.RUNNING)
                self.start_step_timer()
                
                # Get specific params for this task from the config
                task_params = config.get("params", {}).get(step_key, {})
                
                success = task.run(task_params)

                if success:
                    self.update_step_state(step_key, StepStatus.SUCCESS)
                    self.doc.save() # Checkpoint save
                else:
                    self.update_step_state(step_key, StepStatus.FAILED)
                    raise Exception(f"Task {step_key} returned False.")

            # 5. Finalize
            self.update_progress(step="Finished", progress=100)
            update_job_status(self.job_id, status=JobStatus.COMPLETED)

        except Exception as e:
            print(f"Workflow Error: {str(e)}")
            update_job_status(self.job_id, status=JobStatus.FAILED, error_msg=str(e))

    def update_step_state(self, step: str, status: StepStatus):
        """Updates the step-specific status for the frontend node graph."""
        self.steps_state[step] = status
        update_job_status(self.job_id, step_states=self.steps_state)

    def _load_or_create_project(self):
        """Initializes the .psx file structure."""
        project_name = "project.psx"
        path = os.path.join(self.output_folder, project_name)
        
        if os.path.exists(path):
            self.doc.open(path)
            # Use the first chunk found or create one
            if len(self.doc.chunks) > 0:
                self.chunk = self.doc.chunk
            else:
                self.chunk = self.doc.addChunk()
        else:
            # Document must be saved before adding chunks in some Metashape versions
            self.doc.save(path)
            self.chunk = self.doc.addChunk()
            self.doc.save()