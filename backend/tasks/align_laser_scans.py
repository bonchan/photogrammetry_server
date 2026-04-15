import Metashape # type: ignore
from tasks.base_task import BaseTask

class AlignLaserScansTask(BaseTask):
  def validate_dependencies(self) -> bool:
    raise NotImplementedError()

  def run(self, params: dict) -> bool:
    raise NotImplementedError()