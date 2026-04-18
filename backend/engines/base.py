from abc import ABC, abstractmethod
from typing import List

class PhotogrammetryEngine(ABC):
    """
    The universal contract for all photogrammetry providers.
    All engine implementations (Metashape, WebODM, etc.) must 
    inherit from this class.
    """
    def __init__(self, dataset_name: str, input_dir: str, output_dir: str):
        self.dataset_name = dataset_name
        self.input_dir = input_dir
        self.output_dir = output_dir

    # --- 1. Project Management ---
    @abstractmethod
    def load_project(self, read_only: bool = False):
        """Initializes or opens the project file/environment."""
        pass

    @abstractmethod
    def save_project(self):
        """Persists the current state of the project."""
        pass

    @abstractmethod
    def get_completed_tasks(self) -> List[str]:
        """Checks the project data to see which tasks are physically finished."""
        pass

    @abstractmethod
    def sync_state_file(self):
        """Writes the current completion state to the tasks.json file."""
        pass

    @abstractmethod
    def get_pipeline(self, profile_name: str) -> list:
        pass

    @abstractmethod
    def get_template(self, template_name: str) -> dict:
        pass

    @classmethod
    @abstractmethod
    def get_info(cls) -> dict:
        """Returns engine metadata and available pipelines."""
        pass

    # --- 2. Pipeline Execution ---
    @abstractmethod
    def execute_task(self, task_name: str, params: dict) -> bool:
        """
        The primary entry point for the Worker.
        Routes a generic task name to engine-specific internal tasks.
        """
        pass