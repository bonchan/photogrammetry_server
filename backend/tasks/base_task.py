from abc import ABC, abstractmethod
from typing import Any, Dict
from core.enums import TaskType

class BaseTask(ABC):
  def __init__(self, worker: Any):
    self.worker = worker
    self.chunk = worker.chunk

  @abstractmethod
  def run(self, params: Dict[str, Any]) -> bool:
    """The main execution logic for the task."""
    pass

  def validate_dependencies(self) -> bool:
    """Override this to check if required Metashape objects exist."""
    return True

  def progress_wrapper(self, p: float):
    """Passes Metashape progress back to the orchestrator."""
    # TaskType is handled by the worker's current step name
    self.worker.update_progress(self.worker.current_step, p)

  def progress_callback(self, p):
        return self.worker.progress_callback(p)

  def log(self, message: str):
    # This reaches into the MockWorker we built in test_worker.py
    if hasattr(self.worker, 'log'):
        self.worker.log(message)
    else:
        print(f"[FALLBACK LOG] {message}")