import os
from core.enums import TaskType
import Metashape

class MetashapeService:
    def __init__(self, dataset_name: str):
        self.dataset_name = dataset_name
        self.output_path = os.path.abspath(f"../_outputs/{dataset_name}_out")
        self.psx_path = os.path.join(self.output_path, f"{dataset_name}.psx")
        self.export_path = os.path.join(self.output_path, "exports")

        self.expected_files = {
            "ortho": f"{self.dataset_name}_ortho.tif",
            "dem": f"{self.dataset_name}_dem.tif",
            "model": f"{self.dataset_name}_model.obj",
            "point_cloud": f"{self.dataset_name}_pc.las",
            "map_tiles": f"{self.dataset_name}_map_tiles.zip",
            "report": f"{self.dataset_name}_report.pdf"
        }

        # Keep state in memory
        self.doc = None
        self.chunk = None

    def load_project(self, read_only=False):
        """Opens or creates the project and stores it in memory."""
        if self.doc: 
            return # Already loaded!

        self.doc = Metashape.Document()
        
        if os.path.exists(self.psx_path):
            # Open existing
            self.doc.open(self.psx_path, read_only=read_only, ignore_lock=read_only)

            if not read_only and self.doc.read_only:
                raise PermissionError(
                    f"FATAL: {self.dataset_name}.psx is locked by another program "
                    "(probably the Metashape GUI). Close it before running the worker!"
                )
            
            if self.doc.chunks:
                self.chunk = self.doc.chunks[0]
            else:
                if not read_only:
                  os.makedirs(self.output_path, exist_ok=True)
                  self.doc.save(self.psx_path)
                  self.chunk = self.doc.addChunk()
                  self.doc.save()
        else:
            # Create new (Only if we have write permission)
            if not read_only:
                os.makedirs(self.output_path, exist_ok=True)
                self.doc.save(self.psx_path)
                self.chunk = self.doc.addChunk()
                self.doc.save()

    def save_project(self):
        """Saves the project safely without breaking internal paths."""
        if self.doc:
            # If the document already has an internal path established, 
            # do a normal 'save' to prevent the "Save As" bug.
            if self.doc.path:
                self.doc.save() 
            else:
                # Fallback for brand-new, unsaved documents
                self.doc.save(self.psx_path)

    def get_export_status(self) -> dict:
        export_status = {}
        for key, filename in self.expected_files.items():
            full_path = os.path.join(self.export_path, filename)
            export_status[key] = os.path.exists(full_path)
        return export_status

    def get_completed_steps(self) -> list:
        completed_steps = []
        
        # Ensure project is loaded (defaults to read_only if not loaded yet)
        if not self.doc:
            if not os.path.exists(self.psx_path):
                return completed_steps # Nothing to load
            self.load_project(read_only=True)

        if not self.chunk:
            return completed_steps

        try:
            # 1. Internal checks (Using self.chunk instead of a local variable)
            if len(self.chunk.cameras) > 0: completed_steps.append(TaskType.ADD_PHOTOS)
            if self.chunk.tie_points and any(c.transform for c in self.chunk.cameras if c.transform): completed_steps.append(TaskType.ALIGN_PHOTOS)
            if self.chunk.depth_maps: completed_steps.append(TaskType.DEPTH_MAPS)
            if self.chunk.model: completed_steps.append(TaskType.MODEL)
            if self.chunk.model and len(self.chunk.model.tex_vertices) > 0: completed_steps.append(TaskType.UV)
            if self.chunk.model and self.chunk.model.textures: completed_steps.append(TaskType.TEXTURE)
            if self.chunk.elevation: completed_steps.append(TaskType.DEM)
            if self.chunk.orthomosaic: completed_steps.append(TaskType.ORTHO)
            if self.chunk.point_cloud: completed_steps.append(TaskType.POINT_CLOUD)
            if self.chunk.tiled_model: completed_steps.append(TaskType.TILED_MODEL)

            # 2. Export checks
            exports = self.get_export_status()
            for asset_type, exists in exports.items():
                if exists:
                    completed_steps.append(f"export_{asset_type}")

        except Exception as e:
            print(f"Service Error: {e}")
        
        return completed_steps