import os
import shutil
from tasks.base_task import BaseTask

class CleanupTask(BaseTask):
  def run(self, params: dict) -> bool:
    self.log("Starting project cleanup and optimization...")
    
    # 1. Clear the Metashape internal cache
    # This is the biggest space-saver
    try:
      self.doc.clear() 
      self.log("Metashape internal cache cleared.")
    except Exception as e:
      self.log(f"Warning: Could not clear cache: {e}")

    # 2. Compact the project
    # This removes 'ghost' data from the .psx database
    self.doc.save(os.path.join(self.worker.output_folder, "project.psx"), 
                  compression=9, 
                  absolute_paths=False)

    # 3. Optional: Delete the .files folder if user only wants exports
    # WARNING: This makes the .psx unopenable, use only if "Export-Only" mode is on.
    if params.get("delete_project_files", False):
      files_path = os.path.join(self.worker.output_folder, "project.files")
      if os.path.exists(files_path):
        shutil.rmtree(files_path)
        self.log("Deleted .files directory to save space.")

    self.log("Cleanup complete. Project is ready for archiving.")
    return True