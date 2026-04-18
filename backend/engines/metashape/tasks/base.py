from abc import ABC, abstractmethod
from typing import Any, Dict

class MetashapeTaskBase(ABC):
    def __init__(self, engine):
        """
        We pass the ENGINE here. 
        The Engine holds the 'doc' and 'chunk'.
        """
        self.engine = engine
        # Accessing Metashape objects safely via the engine
        self.doc = getattr(engine, 'doc', None)
        self.chunk = getattr(engine, 'chunk', None)

    @abstractmethod
    def run(self, params: Dict[str, Any]) -> bool:
        """The main execution logic for the task."""
        pass

    def validate_dependencies(self) -> bool:
        """Override this to check if required Metashape objects exist."""
        if not self.chunk:
            self.log("Dependency Error: No active chunk found.")
            return False
        return True
    
    def is_completed(self) -> bool:
        """
        Checks the physical Metashape project to see if this task is already done.
        Override this in specific tasks.
        """
        return False

    def log(self, message: str):
        """
        Route logs through the engine's logger 
        (which eventually reaches the worker).
        """
        print(f"[TASK LOG] {message}")
