import Metashape # type: ignore
from typing import Dict, Any, List, Optional
from tasks.base_task import BaseTask

class BuildDepthMapsTask(BaseTask):
  def validate_dependencies(self) -> bool:
    """
    Level 3 Dependency: Requires aligned cameras (Level 1).
    """
    if not self.chunk or len(self.chunk.cameras) == 0:
      self.log("Error: No cameras found.")
      return False
      
    aligned_cameras = [c for c in self.chunk.cameras if c.transform]
    if len(aligned_cameras) < 2:
      self.log("Error: At least 2 aligned cameras required.")
      return False
      
    return True

  def run(self, params: Dict[str, Any]) -> bool:
    """
    Executes the Build Depth Maps workflow.
    """
    self.log("Generating Depth Maps (Full Spec)...")
    return self._build_depth_maps_documented(**params)

  def _build_depth_maps_documented(
    self,
    downscale: int = 4,
    filter_mode: Metashape.FilterMode = Metashape.MildFiltering,
    cameras: List[int] = [],
    reuse_depth: bool = False,
    max_neighbors: int = 16,
    subdivide_task: bool = True,
    workitem_size_cameras: int = 20,
    max_workgroup_size: int = 100
  ) -> bool:
    """
    Generate depth maps for the chunk using official Metashape 2.1.2 specs.

    :param downscale: Depth map quality (1-Ultra high, 2-High, 4-Medium, 8-Low, 16-Lowest).
    :param filter_mode: Depth map filtering mode.
    :param cameras: List of cameras to process (empty for all).
    :param reuse_depth: Enable reuse depth maps option.
    :param max_neighbors: Maximum number of neighbor images to use for depth map generation.
    :param subdivide_task: Enable fine-level task subdivision.
    :param workitem_size_cameras: Number of cameras in a workitem.
    :param max_workgroup_size: Maximum workgroup size.
    """

    self.chunk.buildDepthMaps(
      downscale=downscale,
      filter_mode=filter_mode,
      cameras=cameras,
      reuse_depth=reuse_depth,
      max_neighbors=max_neighbors,
      subdivide_task=subdivide_task,
      workitem_size_cameras=workitem_size_cameras,
      max_workgroup_size=max_workgroup_size,
      progress=self.progress_callback
    )

    return True