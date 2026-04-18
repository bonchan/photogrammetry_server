import Metashape # type: ignore
from .base import MetashapeTaskBase

class BuildTiledModelTask(MetashapeTaskBase):

    def is_completed(self) -> bool:
        """Physical check: Does the tiled model asset exist?"""
        if not self.chunk:
            return False
        return self.chunk.tiled_model is not None

    def validate_dependencies(self, params: dict) -> bool:
        """
        Tiled Model Dependency: Requires specific source data based on config.
        """
        if not self.chunk:
            return False

        # 0=TiePoints, 1=PointCloud, 4=DepthMaps (Default), 6=Mesh
        source_data = params.get("source_data", 4)

        if source_data == 4 and not self.chunk.depth_maps:
            self.log("Error: Tiled Model source set to Depth Maps, but none exist.")
            return False
        elif source_data == 6 and not self.chunk.model:
            self.log("Error: Tiled Model source set to Mesh (Model), but none exists.")
            return False
        elif source_data == 1 and not self.chunk.point_cloud:
            self.log("Error: Tiled Model source set to Point Cloud, but none exists.")
            return False

        return True

    def run(self, params: dict) -> bool:
        # 1. Idempotency Check
        if self.is_completed():
            self.log("Tiled Model already exists. Skipping.")
            return True

        # 2. Dependency Check
        if not self.validate_dependencies(params):
            return False

        # 3. Clean the params for the API call
        progress_cb = params.pop("progress_cb", None)
        kwargs = params.pop("build_tiled_model", params)

        # 4. Handle Enum String Conversions
        if isinstance(kwargs.get("source_data"), str):
            kwargs["source_data"] = getattr(Metashape, kwargs["source_data"])

        # 5. Build Tiled Model
        self.log(f"Generating Tiled Model with {len(kwargs)} parameters...")
        try:
            self.chunk.buildTiledModel(progress=progress_cb, **kwargs)
        except TypeError as e:
            self.log(f"API Parameter Error in buildTiledModel: {e}. Check your JSON keys!")
            return False

        # 6. Verify success
        return self.is_completed()