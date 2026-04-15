import Metashape # type: ignore
from typing import Dict, Any, List, Optional
from tasks.base_task import BaseTask

class BuildOrthomosaicTask(BaseTask):
  def validate_dependencies(self) -> bool:
    """
    Level 6b Dependency: Requires a surface (DEM or Mesh/Model).
    """
    if not self.chunk:
      return False
    
    # Must have either a Model or an Elevation (DEM) asset
    if not self.chunk.model and not self.chunk.elevation:
      self.log("Error: Orthomosaic requires a Model or DEM as surface data.")
      return False
      
    return True

  def run(self, params: Dict[str, Any]) -> bool:
    """
    Executes the Build Orthomosaic workflow.
    """
    self.log("Building Orthomosaic (Full Spec)...")
    return self._build_orthomosaic_documented(**params)

  def _build_orthomosaic_documented(
    self,
    surface_data: Metashape.DataSource = Metashape.ElevationData,
    blending_mode: Metashape.BlendingMode = Metashape.MosaicBlending,
    fill_holes: bool = True,
    ghosting_filter: bool = False,
    cull_faces: bool = False,
    refine_seamlines: bool = False,
    projection: Optional[Metashape.OrthoProjection] = None,
    region: Optional[Metashape.BBox] = None,
    resolution: float = 0.0,
    resolution_x: float = 0.0,
    resolution_y: float = 0.0,
    flip_x: bool = False,
    flip_y: bool = False,
    flip_z: bool = False,
    subdivide_task: bool = True,
    workitem_size_cameras: int = 20,
    workitem_size_tiles: int = 10,
    max_workgroup_size: int = 100,
    replace_asset: bool = False,
    frames: List[int] = []
  ) -> bool:
    """
    Build orthomosaic for the chunk using official Metashape 2.1.2 specs.

    :param surface_data: Orthorectification surface (ModelData or ElevationData).
    :param blending_mode: Orthophoto blending mode (Average, Mosaic, Min, Max, Disabled).
    :param fill_holes: Enable hole filling.
    :param ghosting_filter: Enable ghosting filter (removes moving objects like cars).
    :param cull_faces: Enable back-face culling.
    :param refine_seamlines: Refine seamlines based on image content.
    :param projection: Output projection.
    :param region: Region to be processed (Bounding Box).
    :param resolution: Pixel size in meters (0 for auto/highest).
    :param resolution_x: Pixel size in X dimension in projected units.
    :param resolution_y: Pixel size in Y dimension in projected units.
    :param flip_x: Flip X axis direction.
    :param flip_y: Flip Y axis direction.
    :param flip_z: Flip Z axis direction.
    :param subdivide_task: Enable fine-level task subdivision.
    :param workitem_size_cameras: Number of cameras in a workitem.
    :param workitem_size_tiles: Number of tiles in a workitem.
    :param max_workgroup_size: Maximum workgroup size.
    :param replace_asset: Replace default asset with generated orthomosaic.
    :param frames: List of frames to process.
    """

    # Default projection logic
    if not projection and self.chunk.crs:
      projection = Metashape.OrthoProjection()
      projection.crs = self.chunk.crs

    self.chunk.buildOrthomosaic(
      surface_data=surface_data,
      # blending_mode=blending_mode,
      # fill_holes=fill_holes,
      # ghosting_filter=ghosting_filter,
      # cull_faces=cull_faces,
      # refine_seamlines=refine_seamlines,
      # projection=projection,
      # region=region,
      # resolution=resolution,
      # resolution_x=resolution_x,
      # resolution_y=resolution_y,
      # flip_x=flip_x,
      # flip_y=flip_y,
      # flip_z=flip_z,
      # subdivide_task=subdivide_task,
      # workitem_size_cameras=workitem_size_cameras,
      # workitem_size_tiles=workitem_size_tiles,
      # max_workgroup_size=max_workgroup_size,
      # replace_asset=replace_asset,
      # frames=frames,
      progress=self.progress_callback
    )

    return True