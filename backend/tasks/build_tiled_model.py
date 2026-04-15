import Metashape # type: ignore
from typing import Dict, Any, List, Optional
from tasks.base_task import BaseTask

class BuildTiledModelTask(BaseTask):
  def validate_dependencies(self) -> bool:
    """
    Tiled Model Dependency: Requires Depth Maps or an existing Mesh.
    """
    if not self.chunk:
      return False
    if not self.chunk.depth_maps and not self.chunk.model:
      self.log("Error: Tiled Model requires Depth Maps or an existing Mesh.")
      return False
    return True

  def run(self, params: Dict[str, Any]) -> bool:
    """
    Executes the Build Tiled Model (LOD) workflow.
    """
    self.log("Generating Tiled Model / LOD (Full Spec)...")
    return self._build_tiled_model_documented(**params)

  def _build_tiled_model_documented(
    self,
    pixel_size: float = 0.0,
    tile_size: int = 256,
    source_data: Metashape.DataSource = Metashape.DepthMapsData,
    face_count: int = 20000,
    ghosting_filter: bool = False,
    transfer_texture: bool = False,
    keep_depth: bool = True,
    merge: bool = False,
    operand_chunk: int = -1,
    operand_frame: int = -1,
    operand_asset: int = -1,
    classes: List[int] = [],
    subdivide_task: bool = True,
    workitem_size_cameras: int = 20,
    max_workgroup_size: int = 100,
    replace_asset: bool = False,
    frames: List[int] = []
  ) -> bool:
    """
    Build tiled model for the chunk using official Metashape 2.1.2 specs.

    :param pixel_size: Target model resolution in meters (0 for auto).
    :param tile_size: Size of tiles in pixels (default 256).
    :param source_data: Selects between point cloud, depth maps, or mesh.
    :param face_count: Number of faces per megapixel of texture resolution.
    :param ghosting_filter: Enable ghosting filter.
    :param transfer_texture: Transfer source model texture to tiled model.
    :param keep_depth: Enable store depth maps option.
    :param merge: Merge tiled model flag.
    :param operand_chunk: Operand chunk key.
    :param operand_frame: Operand frame key.
    :param operand_asset: Operand asset key.
    :param classes: Point classes to use for surface extraction.
    :param subdivide_task: Enable fine-level task subdivision.
    :param workitem_size_cameras: Number of cameras in a workitem.
    :param max_workgroup_size: Maximum workgroup size.
    :param replace_asset: Replace default asset with generated tiled model.
    :param frames: List of frames to process.
    """

    self.chunk.buildTiledModel(
      pixel_size=pixel_size,
      tile_size=tile_size,
      source_data=source_data,
      face_count=face_count,
      ghosting_filter=ghosting_filter,
      transfer_texture=transfer_texture,
      keep_depth=keep_depth,
      merge=merge,
      operand_chunk=operand_chunk,
      operand_frame=operand_frame,
      operand_asset=operand_asset,
      classes=classes,
      subdivide_task=subdivide_task,
      workitem_size_cameras=workitem_size_cameras,
      max_workgroup_size=max_workgroup_size,
      replace_asset=replace_asset,
      frames=frames,
      progress=self.progress_callback
    )

    return True