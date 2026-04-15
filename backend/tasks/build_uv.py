# backend/tasks/build_uv.py

import Metashape # type: ignore
from tasks.base_task import BaseTask

class BuildUVTask(BaseTask):
    def validate_dependencies(self):
        # UV mapping requires a 3D Model (Mesh) to exist first
        if not self.chunk.model:
            self.log("Error: No model found. Build model before UV.")
            return False
        return True

    def run(self, params):
        self.log("Generating UV mapping for the model...")
        
        # PINNING THE PARAMETERS
        # We default to GenericMapping (best for general 3D)
        mapping = params.get("mapping_mode", Metashape.GenericMapping)
        
        # Ensure mapping is the correct type even if passed as a string/index
        if isinstance(mapping, str):
            mapping = getattr(Metashape, mapping, Metashape.GenericMapping)

        try:
            self.chunk.buildUV(
                mapping_mode=mapping,
                page_count=params.get("page_count", 1),
                texture_size=params.get("texture_size", 4096), # 8192 for high, 4096 for fast
                progress=self.progress_callback
            )
            return True
        except Exception as e:
            self.log(f"UV Mapping Failed: {e}")
            return False