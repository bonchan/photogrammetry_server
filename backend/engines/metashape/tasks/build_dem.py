import Metashape # type: ignore
from .base import MetashapeTaskBase

class BuildDemTask(MetashapeTaskBase):

    def is_completed(self) -> bool:
        """Physical check: Does the DEM asset exist in the chunk?"""
        if not self.chunk:
            return False
        # Metashape internal property for DEM is 'elevation'
        return self.chunk.elevation is not None

    def validate_dependencies(self, params: dict) -> bool:
        """
        DEM Dependency: Requires Point Cloud (formerly Dense Cloud) or Tie Points.
        """
        if not self.chunk:
            return False

        # source_data: 0=TiePoints, 1=PointCloud (Default), 5=LaserScans
        source_data = params.get("source_data", 1)

        if source_data == 1 and not self.chunk.point_cloud:
            self.log("Error: DEM source set to Point Cloud, but none exists.")
            return False
        elif source_data == 0 and not self.chunk.tie_points:
            self.log("Error: DEM source set to Tie Points, but none exist.")
            return False
        
        if not self.chunk.crs:
            self.log("Error: DEM requires a Coordinate Reference System (CRS). Align photos first.")
            return False
            
        return True

    def run(self, params: dict) -> bool:
        # 1. Idempotency Check
        if self.is_completed():
            self.log("DEM already exists. Skipping.")
            return True

        # 2. Dependency Check
        if not self.validate_dependencies(params):
            return False

        # 3. Clean the params
        progress_cb = params.pop("progress_cb", None)
        kwargs = params.pop("build_dem", params)

        # 4. Handle Enum String Conversions
        if isinstance(kwargs.get("source_data"), str):
            kwargs["source_data"] = getattr(Metashape, kwargs["source_data"])
        if isinstance(kwargs.get("interpolation"), str):
            kwargs["interpolation"] = getattr(Metashape, kwargs["interpolation"])

        # 5. Handle Projection (Critical for GIS)
        if "projection" not in kwargs and self.chunk.crs:
            projection = Metashape.OrthoProjection()
            projection.crs = self.chunk.crs
            kwargs["projection"] = projection

        # 6. Build DEM
        self.log(f"Building DEM with {len(kwargs)} parameters...")
        try:
            self.chunk.buildDem(progress=progress_cb, **kwargs)
        except TypeError as e:
            self.log(f"API Parameter Error in buildDem: {e}. Check your JSON keys!")
            return False

        # 7. Verify success
        return self.is_completed()