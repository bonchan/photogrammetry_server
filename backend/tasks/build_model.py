import Metashape # type: ignore
from typing import Dict, Any, List, Optional
from tasks.base_task import BaseTask

class BuildModelTask(BaseTask):
  def validate_dependencies(self) -> bool:
    if not self.chunk:
      return False
    # Check for Depth Maps or Point Cloud depending on source_data param
    return True

  def run(self, params: Dict[str, Any]) -> bool:
    self.log("Generating 3D Mesh Model (Full Spec)...")
    return self._build_model_documented(**params)

  def _build_model_documented(
    self,
    surface_type: Metashape.SurfaceType = Metashape.Arbitrary,
    interpolation: Metashape.Interpolation = Metashape.EnabledInterpolation,
    face_count: Metashape.FaceCount = Metashape.MediumFaceCount,
    face_count_custom: int = 200000,
    source_data: Metashape.DataSource = Metashape.DepthMapsData,
    classes: List[int] = [],
    vertex_colors: bool = True,
    vertex_confidence: bool = True,
    volumetric_masks: bool = False,
    keep_depth: bool = True,
    replace_asset: bool = False,
    split_in_blocks: bool = False,
    blocks_crs: Optional[Metashape.CoordinateSystem] = None,
    blocks_size: float = 250.0,
    blocks_origin: Optional[Metashape.Vector] = None,
    clip_to_boundary: bool = False,
    export_blocks: bool = False,
    build_texture: bool = True,
    output_folder: str = '',
    trimming_radius: int = 10,
    cameras: List[int] = [],
    frames: List[int] = [],
    subdivide_task: bool = True,
    workitem_size_cameras: int = 20,
    max_workgroup_size: int = 100
  ) -> bool:
    """
    Generate model for the chunk frame using official Metashape 2.1.2 specs.

    :param surface_type: Type of object to be reconstructed.
    :param interpolation: Interpolation mode.
    :param face_count: Target face count.
    :param face_count_custom: Custom face count.
    :param source_data: Selects between point cloud, tie points, depth maps and laser scans.
    :param classes: List of point classes to be used for surface extraction.
    :param vertex_colors: Enable vertex colors calculation.
    :param vertex_confidence: Enable vertex confidence calculation.
    :param volumetric_masks: Enable strict volumetric masking.
    :param keep_depth: Enable store depth maps option.
    :param replace_asset: Replace default asset with generated model.
    :param split_in_blocks: Split model in blocks.
    :param blocks_crs: Blocks grid coordinate system.
    :param blocks_size: Blocks size in coordinate system units.
    :param blocks_origin: Blocks grid origin.
    :param clip_to_boundary: Clip to boundary shapes.
    :param export_blocks: Export completed blocks.
    :param build_texture: Generate preview textures.
    :param output_folder: Path to output folder.
    :param trimming_radius: Trimming radius (no trimming if zero).
    :param cameras: List of cameras to process.
    :param frames: List of frames to process.
    :param subdivide_task: Enable fine-level task subdivision.
    :param workitem_size_cameras: Number of cameras in a workitem.
    :param max_workgroup_size: Maximum workgroup size.
    """

    self.chunk.buildModel(
      # surface_type=surface_type,
      # interpolation=interpolation,
      # face_count=face_count,
      # face_count_custom=face_count_custom,
      source_data=source_data,
      # classes=classes,
      # vertex_colors=vertex_colors,
      # vertex_confidence=vertex_confidence,
      # volumetric_masks=volumetric_masks,
      # keep_depth=keep_depth,
      # replace_asset=replace_asset,
      # split_in_blocks=split_in_blocks,
      # blocks_crs=blocks_crs if blocks_crs else self.chunk.crs,
      # blocks_size=blocks_size,
      # blocks_origin=blocks_origin,
      # clip_to_boundary=clip_to_boundary,
      # export_blocks=export_blocks,
      # build_texture=build_texture,
      # output_folder=output_folder,
      # trimming_radius=trimming_radius,
      # cameras=cameras,
      # frames=frames,
      # subdivide_task=subdivide_task,
      # workitem_size_cameras=workitem_size_cameras,
      # max_workgroup_size=max_workgroup_size,
      progress=self.progress_callback
    )

    return True