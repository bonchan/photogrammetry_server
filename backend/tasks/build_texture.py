import Metashape # type: ignore
from typing import Dict, Any, List, Optional
from tasks.base_task import BaseTask

class BuildTextureTask(BaseTask):
  def validate_dependencies(self) -> bool:
    """
    Level 6a Dependency: Requires a Model (Mesh).
    """
    if not self.chunk or not self.chunk.model:
      self.log("Error: buildTexture requires an existing Model (Mesh).")
      return False
    return True

  def run(self, params: Dict[str, Any]) -> bool:
    """
    Executes the Build Texture workflow.
    """
    self.log("Generating Model Texture (Full Spec)...")
    return self._build_texture_documented(**params)

  def _build_texture_documented(
    self,
    blending_mode: Metashape.BlendingMode = Metashape.MosaicBlending,
    texture_size: int = 8192,
    fill_holes: bool = True,
    ghosting_filter: bool = True,
    cameras: List[int] = [],
    texture_type: Metashape.Model.TextureType = Metashape.Model.DiffuseMap,
    source_model: int = -1,
    transfer_texture: bool = True,
    workitem_size_cameras: int = 20,
    max_workgroup_size: int = 100,
    anti_aliasing: int = 1
  ) -> bool:
    """
    Generate texture for the chunk using official Metashape 2.1.2 specs.

    :param blending_mode: Texture blending mode.
    :param texture_size: Texture page size (e.g., 4096, 8192, 16384).
    :param fill_holes: Enable hole filling.
    :param ghosting_filter: Enable ghosting filter.
    :param cameras: List of cameras to be used for texturing.
    :param texture_type: Texture type (DiffuseMap, NormalMap, OcclusionMap).
    :param source_model: Source model index.
    :param transfer_texture: Transfer texture from source.
    :param workitem_size_cameras: Number of cameras in a workitem.
    :param max_workgroup_size: Maximum workgroup size.
    :param anti_aliasing: Anti-aliasing coefficient for baking.
    """

    self.chunk.buildTexture(
      blending_mode=blending_mode,
      texture_size=texture_size,
      fill_holes=fill_holes,
      ghosting_filter=ghosting_filter,
      cameras=cameras,
      texture_type=texture_type,
      source_model=source_model,
      transfer_texture=transfer_texture,
      workitem_size_cameras=workitem_size_cameras,
      max_workgroup_size=max_workgroup_size,
      anti_aliasing=anti_aliasing,
      progress=self.progress_callback
    )

    return True