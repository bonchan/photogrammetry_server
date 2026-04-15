import Metashape # type: ignore
from typing import Dict, Any, List, Optional
from tasks.base_task import BaseTask

class BuildPanoramaTask(BaseTask):
  def validate_dependencies(self) -> bool:
    """
    Panorama Dependency: Requires aligned cameras at the same station.
    """
    if not self.chunk or len(self.chunk.cameras) == 0:
      return False
    return True

  def run(self, params: Dict[str, Any]) -> bool:
    """
    Executes the Build Panorama workflow.
    """
    self.log("Generating Spherical Panoramas (Full Spec)...")
    return self._build_panorama_documented(**params)

  def _build_panorama_documented(
    self,
    blending_mode: Metashape.BlendingMode = Metashape.MosaicBlending,
    ghosting_filter: bool = False,
    rotation: Optional[Metashape.Matrix] = None,
    region: Optional[Metashape.BBox] = None,
    width: int = 0,
    height: int = 0,
    camera_groups: List[int] = [],
    frames: List[int] = []
  ) -> bool:
    """
    Generate spherical panoramas from camera stations using official Metashape 2.1.2 specs.

    :param blending_mode: Panorama blending mode.
    :param ghosting_filter: Enable ghosting filter.
    :param rotation: Panorama 3x3 orientation matrix.
    :param region: Bounding box region to generate.
    :param width: Width of output panorama (0 for auto).
    :param height: Height of output panorama (0 for auto).
    :param camera_groups: List of camera groups to process.
    :param frames: List of frames to process.
    """

    self.chunk.buildPanorama(
      blending_mode=blending_mode,
      ghosting_filter=ghosting_filter,
      rotation=rotation,
      region=region,
      width=width,
      height=height,
      camera_groups=camera_groups,
      frames=frames,
      progress=self.progress_callback
    )

    return True 