import os
import json
from pathlib import Path
# import ODM

from engines.base import PhotogrammetryEngine
from .enums import ODMTask

# from .pipelines import ODM_PIPELINES
# from .templates import ODM_TEMPLATES

# from .tasks import (
#     DummyTask,
#     AddPhotosTask,
#     AlignPhotosTask,
#     BuildDepthMapsTask,
#     BuildPointCloudTask,
#     BuildModelTask,
#     BuildUVTask,
#     BuildTextureTask,
#     BuildTiledModelTask,
#     BuildDemTask,
#     BuildOrthomosaicTask,
#     ExportResultsTask
# )

# from tasks import DetectionTask

class ODMEngine(PhotogrammetryEngine):
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
        # return ODM_PIPELINES.get(profile_name, {}).get("tasks", [])
        return {}

    def get_template(self, template_name: str) -> dict:
        """Returns the parameter dictionary for a given template."""
        # return ODM_TEMPLATES.get(template_name, {}).get("params", {})
        return {}

    @property
    def registry(self) -> dict:
        """The Capability Map"""
        return {
            # ODMTask.ADD_PHOTOS: AddPhotosTask,
            # ODMTask.ALIGN_PHOTOS: AlignPhotosTask,
            # # ODMTask.ALIGNMENT_LASER_SCANS: DummyTask,
            # ODMTask.DEPTH_MAPS: BuildDepthMapsTask,
            # ODMTask.MODEL: BuildModelTask,
            # ODMTask.UV: BuildUVTask,
            # ODMTask.TEXTURE: BuildTextureTask,
            # ODMTask.TILED_MODEL: BuildTiledModelTask,
            # ODMTask.POINT_CLOUD: BuildPointCloudTask,
            # ODMTask.DEM: BuildDemTask,
            # ODMTask.ORTHO: BuildOrthomosaicTask,
            # # ODMTask.DETECTION: DetectionTask,
            # ODMTask.EXPORT: ExportResultsTask,
            # ODMTask.CLEANUP: DummyTask,
        }

    # --- 1. PROJECT MANAGEMENT ---

    def load_project(self, read_only=False):
        """Opens or creates the project and stores it in memory."""
        pass

    def save_project(self):
        """Saves the project safely."""
        pass

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
        return completed_tasks

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
        # for key, val in ODM_PIPELINES.items():
        #     safe_pipelines.append({
        #         "id": key,
        #         "name": val["name"],
        #         "description": val.get("description", ""),
        #         "required_asset": val["required_asset"]
        #     })
            
        return {
            "id": "ODM",
            "name": "Open Drone Map",
            "pipelines": safe_pipelines
        }

    # --- 3. EXECUTION ---

    def execute_task(self, task_name: ODMTask, params: dict) -> bool:
        """Dispatches the task to the correct specialist class."""
        task_class = self.registry.get(task_name)
        
        if not task_class:
            print(f"ODMEngine doesn't support task: {task_name}")
            return False
        
        # Instantiate the specialist and run it
        executor = task_class(engine=self)
        return executor.run(params)
