from pathlib import Path
from .base import MetashapeTaskBase

ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.tif', '.tiff', '.png'}

class AddPhotosTask(MetashapeTaskBase):
    
    def is_completed(self) -> bool:
        """Strict validation: checks if all disk files are in the chunk."""
        if not self.chunk or len(self.chunk.cameras) == 0:
            return False
            
        image_folder = Path(self.engine.input_dir)
        if not image_folder.exists():
            return False
            
        disk_files = [f for f in image_folder.iterdir() if f.suffix.lower() in ALLOWED_EXTENSIONS]
        return len(self.chunk.cameras) == len(disk_files)

    def run(self, params: dict) -> bool:
        # 1. Use your own validation to prevent duplicate work!
        if self.is_completed():
            self.log("All photos are already present. Skipping.")
            return True
            
        # 2. Gather files
        image_folder = Path(self.engine.input_dir)
        disk_files = [
            str(f.resolve()) for f in image_folder.iterdir() 
            if f.suffix.lower() in ALLOWED_EXTENSIONS
        ]
        
        # 3. Add to chunk
        if len(self.chunk.cameras) > 0:
            self.log(f"Clearing {len(self.chunk.cameras)} existing cameras to prevent duplicates...")
            self.chunk.remove(self.chunk.cameras)
        self.chunk.addPhotos(disk_files)
        
        # 4. Final verification using the same logic
        return self.is_completed()