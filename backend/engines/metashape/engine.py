import os
import json
from pathlib import Path
import Metashape

from engines.base import PhotogrammetryEngine
from .enums import MetashapeTask

from .pipelines import METASHAPE_PIPELINES
from .templates import METASHAPE_TEMPLATES

from .tasks import (
    DummyTask,
    AddPhotosTask,
    AlignPhotosTask,
    BuildDepthMapsTask,
    BuildPointCloudTask,
    BuildModelTask,
    BuildUVTask,
    BuildTextureTask,
    BuildTiledModelTask,
    BuildDemTask,
    BuildOrthomosaicTask,
    ExportResultsTask
)

# from tasks import DetectionTask

class MetashapeEngine(PhotogrammetryEngine):
    def __init__(self, dataset_name: str, input_dir: str, output_dir: str):
        # We pass output_dir from the factory now, keeping the engine OS-agnostic
        super().__init__(dataset_name, input_dir, output_dir)
        
        # Use pathlib for clean, cross-platform paths
        self.output_path = Path(self.output_dir)
        self.psx_path = self.output_path / f"{self.dataset_name}.psx"
        self.export_path = self.output_path / "exports"
        self.state_file = self.output_path / "tasks.json" # Kept as tasks.json per your UI

        self.expected_files = {
            "ortho": f"{self.dataset_name}_ortho",
            "dem": f"{self.dataset_name}_dem.tif",
            "model": f"{self.dataset_name}_model.obj",
            "point_cloud": f"{self.dataset_name}_pc.las",
            "map_tiles": f"{self.dataset_name}_map_tiles.zip",
            "report": f"{self.dataset_name}_report.pdf"
        }

        self.doc = None
        self.chunk = None

    def get_pipeline(self, profile_name: str) -> list:
        """Returns the list of tasks for a given profile."""
        return METASHAPE_PIPELINES.get(profile_name, {}).get("tasks", [])

    def get_template(self, template_name: str) -> dict:
        """Returns the parameter dictionary for a given template."""
        return METASHAPE_TEMPLATES.get(template_name, {}).get("params", {})

    @property
    def registry(self) -> dict:
        """The Capability Map"""
        return {
            MetashapeTask.ADD_PHOTOS: AddPhotosTask,
            MetashapeTask.ALIGN_PHOTOS: AlignPhotosTask,
            # MetashapeTask.ALIGNMENT_LASER_SCANS: DummyTask,
            MetashapeTask.DEPTH_MAPS: BuildDepthMapsTask,
            MetashapeTask.MODEL: BuildModelTask,
            MetashapeTask.UV: BuildUVTask,
            MetashapeTask.TEXTURE: BuildTextureTask,
            MetashapeTask.TILED_MODEL: BuildTiledModelTask,
            MetashapeTask.POINT_CLOUD: BuildPointCloudTask,
            MetashapeTask.DEM: BuildDemTask,
            MetashapeTask.ORTHO: BuildOrthomosaicTask,
            # MetashapeTask.DETECTION: DetectionTask,
            MetashapeTask.EXPORT: ExportResultsTask,
            MetashapeTask.CLEANUP: DummyTask,
        }

    # --- 1. PROJECT MANAGEMENT ---

    def load_project(self, read_only=False):
        """Opens or creates the project and stores it in memory."""
        if self.doc: 
            return

        self.doc = Metashape.Document()
        
        if self.psx_path.exists():
            self.doc.open(str(self.psx_path), read_only=read_only, ignore_lock=True)

            if not read_only and self.doc.read_only:
                raise PermissionError(f"FATAL: {self.psx_path.name} is locked by another program.")
            
            if self.doc.chunks:
                self.chunk = self.doc.chunks[0]
            elif not read_only:
                self.output_path.mkdir(parents=True, exist_ok=True)
                self.doc.save(str(self.psx_path))
                self.chunk = self.doc.addChunk()
                self.doc.save()
        else:
            if not read_only:
                self.output_path.mkdir(parents=True, exist_ok=True)
                self.doc.save(str(self.psx_path))
                self.chunk = self.doc.addChunk()
                self.doc.save()

    def save_project(self):
        """Saves the project safely."""
        if self.doc:
            if self.doc.path:
                self.doc.save() 
            else:
                self.doc.save(str(self.psx_path))

    # --- 2. STATE VERIFICATION ---

    def get_export_status(self) -> dict:
        export_status = {}
        for key, filename in self.expected_files.items():
            full_path = self.export_path / filename
            export_status[key] = full_path.exists()
        return export_status

    def get_completed_tasks(self) -> list:
        """Physical verification of the .psx content."""
        completed_tasks = []
        
        if not self.doc:
            if not self.psx_path.exists():
                return completed_tasks
            self.load_project(read_only=True)

        if not self.chunk:
            return completed_tasks
        
        for task_enum, task_class in self.registry.items():
            try:
                # Instantiate the task specialist
                task_instance = task_class(engine=self)
                
                # Ask the specialist if it's done
                if task_instance.is_completed():
                    completed_tasks.append(task_enum)
            except Exception as e:
                # If a task errors during check, assume it needs to run
                print(f"  [Warning] Error checking completion for {task_enum}: {e}")
                
        return completed_tasks

        # try:
        #     # Internal checks
        #     if len(self.chunk.cameras) > 0: completed_tasks.append(MetashapeTask.ADD_PHOTOS)
        #     if self.chunk.tie_points and any(c.transform for c in self.chunk.cameras if c.transform): completed_tasks.append(MetashapeTask.ALIGN_PHOTOS)
        #     if self.chunk.depth_maps: completed_tasks.append(MetashapeTask.DEPTH_MAPS)
        #     if self.chunk.model: completed_tasks.append(MetashapeTask.MODEL)
        #     if self.chunk.model and len(self.chunk.model.tex_vertices) > 0: completed_tasks.append(MetashapeTask.UV)
        #     if self.chunk.model and self.chunk.model.textures: completed_tasks.append(MetashapeTask.TEXTURE)
        #     if self.chunk.elevation: completed_tasks.append(MetashapeTask.DEM)
        #     if self.chunk.orthomosaic: completed_tasks.append(MetashapeTask.ORTHO)
        #     if self.chunk.point_cloud: completed_tasks.append(MetashapeTask.POINT_CLOUD)
        #     if self.chunk.tiled_model: completed_tasks.append(MetashapeTask.TILED_MODEL)

        #     # Export checks
        #     exports = self.get_export_status()
        #     for asset_type, exists in exports.items():
        #         if exists:
        #             completed_tasks.append(f"export_{asset_type}")

        # except Exception as e:
        #     print(f"Engine State Error: {e}")

    def sync_state_file(self):
        """Safely writes the tasks.json state file."""
        completed = self.get_completed_tasks()
        state_data = {"completed_tasks": completed}
        
        # pathlib equivalent of adding .tmp
        temp_file = self.state_file.with_suffix('.json.tmp')
        try:
            with open(temp_file, "w") as f:
                json.dump(state_data, f)
            # os.replace is still the safest cross-platform atomic swap
            os.replace(temp_file, self.state_file)
        except Exception as e:
            print(f"Failed to sync state file: {e}")

    @classmethod
    def get_info(cls) -> dict:
        # Strip out the internal tasks, send only UI-safe data
        safe_pipelines = []
        for key, val in METASHAPE_PIPELINES.items():
            safe_pipelines.append({
                "id": key,
                "name": val["name"],
                "description": val.get("description", ""),
                "required_asset": val["required_asset"]
            })
            
        return {
            "id": "metashape",
            "name": "Agisoft Metashape",
            "pipelines": safe_pipelines
        }

    # --- 3. EXECUTION ---

    def execute_task(self, task_name: MetashapeTask, params: dict) -> bool:
        """Dispatches the task to the correct specialist class."""
        task_class = self.registry.get(task_name)
        
        if not task_class:
            print(f"MetashapeEngine doesn't support task: {task_name}")
            return False
        
        # Instantiate the specialist and run it
        executor = task_class(engine=self)
        return executor.run(params)
