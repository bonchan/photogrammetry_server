


import sys
import os
import zipfile
import json

# Get the directory where worker.py lives (which is the backend folder)
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)



    

import Metashape # type: ignore
from core.enums import TaskType
from tasks import TASK_REGISTRY
from core.templates import PIPELINE_TEMPLATES

class MockWorker:
  def __init__(self, image_folder, output_folder, chunk):
    self.image_folder = image_folder
    self.output_folder = output_folder
    self.chunk = chunk
    self.job_id = 772
    self.interrupted = False

  def log(self, message): # Added log helper for the tasks
    print(f"[LOG] {message}")

  def progress_callback(self, p):
    print(f"      Progress: {p:.1f}%")

def run_test_pipeline():
  # Setup paths
  IMAGE_DIR = os.path.abspath("./_datasets/FM-PP-10") 
  OUTPUT_DIR = os.path.abspath("./_outputs/FM-PP-10")
  if not os.path.exists(OUTPUT_DIR): os.makedirs(OUTPUT_DIR)

  # Initialize Metashape
  doc = Metashape.Document()
  doc.save(os.path.join(OUTPUT_DIR, "test_project.psx"))
  chunk = doc.addChunk()
  worker = MockWorker(IMAGE_DIR, OUTPUT_DIR, chunk)

  # 2. SELECT THE TEMPLATE
  template = PIPELINE_TEMPLATES["FULL_PROCESS"]
  print(f"--- Running Template: {template['label']} ---")

  # 3. DYNAMIC EXECUTION LOOP
  try:
    for task_type in template["pipeline"]:
      task_class = TASK_REGISTRY.get(task_type)
      params = template["params"].get(task_type, {})

      print(f"\n>> STARTING: {task_type.value}")
      
      # Instantiate and Run
      task_instance = task_class(worker)
      
      if not task_instance.validate_dependencies():
        print(f"!! Aborting: Dependencies failed for {task_type.value}")
        break

      # Pass progress callback manually if your task expects it
      # Note: our BaseTask uses self.progress_callback which we mapped in MockWorker
      success = task_instance.run(params)
      
      if success:
        doc.save()
        print(f"<< COMPLETED: {task_type.value}")
      else:
        print(f"!! FAILED: {task_type.value}")
        break

    print(f"\n--- FAST PREVIEW FINISHED ---")

  except Exception as e:
    print(f"\nFATAL ERROR: {str(e)}")

if __name__ == "__main__":
  run_test_pipeline()