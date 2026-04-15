import os
from tasks.base_task import BaseTask
from core.config import ALLOWED_EXTENSIONS 

class AddPhotosTask(BaseTask):
  def run(self, params: dict) -> bool:
      # Check if photos already exist
      if len(self.worker.chunk.cameras) > 0:
          return True

      image_folder = self.worker.image_folder
      
      # Filter files using the tuple from .env
      photos = [
          os.path.join(image_folder, f) 
          for f in os.listdir(image_folder)
          if f.lower().endswith(ALLOWED_EXTENSIONS)
      ]

      if not photos:
          print(f"Error: No photos found matching {ALLOWED_EXTENSIONS}")
          return False

      self.worker.chunk.addPhotos(photos)
      return True