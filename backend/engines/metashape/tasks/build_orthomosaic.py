import Metashape # type: ignore
from .base import MetashapeTaskBase

class BuildOrthomosaicTask(MetashapeTaskBase):

    def is_completed(self) -> bool:
        """Physical check: Does the Orthomosaic asset exist?"""
        if not self.chunk:
            return False
        return self.chunk.orthomosaic is not None

    def validate_dependencies(self, params: dict) -> bool:
        """
        Orthomosaic Dependency: Requires a surface (DEM or Mesh/Model).
        """
        if not self.chunk:
            return False

        # source_data: 6=ModelData, 7=ElevationData (Default)
        source_data = params.get("surface_data", 7)

        if source_data == 7 and not self.chunk.elevation:
            self.log("Error: Orthomosaic surface set to Elevation (DEM), but none exists.")
            return False
        elif source_data == 6 and not self.chunk.model:
            self.log("Error: Orthomosaic surface set to Model (Mesh), but none exists.")
            return False
            
        if not self.chunk.crs:
            self.log("Error: Orthomosaic requires a CRS. Align photos first.")
            return False
            
        return True

    def run(self, params: dict) -> bool:
        # 1. Idempotency Check
        if self.is_completed():
            self.log("Orthomosaic already exists. Skipping.")
            return True

        # 2. Dependency Check
        if not self.validate_dependencies(params):
            return False

        # 3. Clean the params
        progress_cb = params.pop("progress_cb", None)
        kwargs = params.pop("build_orthomosaic", params)

        # 4. Handle Enum String Conversions
        if isinstance(kwargs.get("surface_data"), str):
            kwargs["surface_data"] = getattr(Metashape, kwargs["surface_data"])
        if isinstance(kwargs.get("blending_mode"), str):
            kwargs["blending_mode"] = getattr(Metashape, kwargs["blending_mode"])

        # 5. Handle Projection (Critical for Geo-referencing)
        if "projection" not in kwargs and self.chunk.crs:
            projection = Metashape.OrthoProjection()
            projection.crs = self.chunk.crs
            kwargs["projection"] = projection

        # 6. Build Orthomosaic
        self.log(f"Building Orthomosaic with {len(kwargs)} parameters...")
        try:
            self.chunk.buildOrthomosaic(progress=progress_cb, **kwargs)
        except TypeError as e:
            self.log(f"API Parameter Error in buildOrthomosaic: {e}. Check your config keys!")
            return False

        # 7. Verify success
        return self.is_completed()