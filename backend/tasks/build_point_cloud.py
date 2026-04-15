import Metashape # type: ignore
from typing import Dict, Any, List, Optional
from tasks.base_task import BaseTask

class BuildPointCloudTask(BaseTask):
  def validate_dependencies(self) -> bool:
    """
    Level 4 Dependency: Requires Depth Maps.
    """
    if not self.chunk or not self.chunk.depth_maps:
      self.log("Error: Point Cloud requires Depth Maps.")
      return False
    return True

  def run(self, params: Dict[str, Any]) -> bool:
    """
    Executes the Build Point Cloud (Dense Cloud) workflow.
    """
    self.log("Generating Dense Point Cloud (Full Spec)...")
    return self._build_point_cloud_documented(**params)

  def _build_point_cloud_documented(
    self,
    source_data: Metashape.DataSource = Metashape.DepthMapsData,
    point_colors: bool = True,
    point_confidence: bool = True,
    keep_depth: bool = True,
    max_neighbors: int = 100,
    uniform_sampling: bool = True,
    points_spacing: float = 0.1,
    asset: int = -1,
    subdivide_task: bool = True,
    workitem_size_cameras: int = 20,
    max_workgroup_size: int = 100,
    replace_asset: bool = False,
    frames: List[int] = []
  ) -> bool:
    """
    Generate point cloud for the chunk frame using official Metashape 2.1.2 specs.

    :param source_data: Source data (DepthMapsData, TiePointsData, LaserScanData).
    :param point_colors: Enable point colors calculation.
    :param point_confidence: Enable point confidence calculation.
    :param keep_depth: Enable store depth maps option.
    :param max_neighbors: Max neighbor images to use for filtering.
    :param uniform_sampling: Enable uniform point sampling.
    :param points_spacing: Desired point spacing in meters.
    :param asset: Asset ID to process (-1 for current).
    :param subdivide_task: Enable fine-level task subdivision.
    :param workitem_size_cameras: Number of cameras in a workitem.
    :param max_workgroup_size: Maximum workgroup size.
    :param replace_asset: Replace default asset with generated point cloud.
    :param frames: List of frames to process.
    """

    self.chunk.buildPointCloud(
      source_data=source_data,
      point_colors=point_colors,
      point_confidence=point_confidence,
      keep_depth=keep_depth,
      max_neighbors=max_neighbors,
      uniform_sampling=uniform_sampling,
      points_spacing=points_spacing,
      subdivide_task=subdivide_task,
      workitem_size_cameras=workitem_size_cameras,
      max_workgroup_size=max_workgroup_size,
      replace_asset=replace_asset,
      frames=frames,
      progress=self.progress_callback
    )

    return True