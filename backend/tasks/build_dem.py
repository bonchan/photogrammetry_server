import Metashape # type: ignore
from typing import Dict, Any, List, Optional
from tasks.base_task import BaseTask

class BuildDemTask(BaseTask):
    def validate_dependencies(self) -> bool:
        """
        Level 5b Dependency: Requires Point Cloud or Tie Points.
        """
        if not self.chunk:
            return False
        
        if not self.chunk.tie_points and not self.chunk.point_cloud:
            self.log("Error: DEM requires Tie Points or a Point Cloud.")
            return False
            
        return True

    def run(self, params: Dict[str, Any]) -> bool:
        """
        Executes the Build DEM (Digital Elevation Model) workflow.
        """
        self.log("Building Digital Elevation Model (Full Spec)...")
        return self._build_dem_documented(**params)

    def _build_dem_documented(
        self,
        source_data: Metashape.DataSource = Metashape.PointCloudData,
        interpolation: Metashape.Interpolation = Metashape.EnabledInterpolation,
        projection: Optional[Metashape.OrthoProjection] = None,
        region: Optional[Metashape.BBox] = None,
        classes: Optional[List[int]] = None,
        flip_x: bool = False,
        flip_y: bool = False,
        flip_z: bool = False,
        resolution: float = 0.0,
        subdivide_task: bool = True,
        workitem_size_tiles: int = 10,
        max_workgroup_size: int = 100,
        replace_asset: bool = False,
        frames: Optional[List[int]] = None
    ) -> bool:
        
        # 1. Handle auto-projection safely
        if not projection and self.chunk.crs:
            projection = Metashape.OrthoProjection()
            projection.crs = self.chunk.crs

        # 2. Build the exact dictionary of arguments
        # We start with the guaranteed/required/safe default arguments
        kwargs = {
            "source_data": source_data,
            "interpolation": interpolation,
            "flip_x": flip_x,
            "flip_y": flip_y,
            "flip_z": flip_z,
            "resolution": resolution,
            "subdivide_task": subdivide_task,
            "workitem_size_tiles": workitem_size_tiles,
            "max_workgroup_size": max_workgroup_size,
            "replace_asset": replace_asset,
            "progress": self.progress_callback
        }

        # 3. Safely append optionals ONLY if they are not None
        if projection is not None:
            kwargs["projection"] = projection
            
        if region is not None:
            kwargs["region"] = region
            
        if classes:  # Checks if it's not None and not an empty list
            kwargs["classes"] = classes
            
        if frames:
            kwargs["frames"] = frames

        # 4. Unpack and execute
        # This completely avoids sending NoneTypes to the C++ backend!
        self.chunk.buildDem(**kwargs)

        return True