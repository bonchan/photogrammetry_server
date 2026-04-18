import Metashape # type: ignore
from .base import MetashapeTaskBase

class BuildPointCloudTask(MetashapeTaskBase):

    def is_completed(self) -> bool:
        """Physical check: Does the Point Cloud (Dense Cloud) asset exist?"""
        if not self.chunk:
            return False
        # API 2.1.2: self.chunk.dense_cloud is now self.chunk.point_cloud
        return self.chunk.point_cloud is not None

    def validate_dependencies(self, params: dict) -> bool:
        """
        Dependency Check: Point Cloud usually requires Depth Maps.
        """
        if not self.chunk:
            return False

        # source_data: 0=TiePoints, 4=DepthMaps (Default), 5=LaserScans
        source_data = params.get("source_data", 4)

        if source_data == 4 and not self.chunk.depth_maps:
            self.log("Error: Point Cloud source set to Depth Maps, but none exist.")
            return False
        elif source_data == 0 and not self.chunk.tie_points:
            self.log("Error: Point Cloud source set to Tie Points, but none exist.")
            return False
            
        return True

    def run(self, params: dict) -> bool:
        # 1. Idempotency Check
        if self.is_completed():
            self.log("Point Cloud already exists. Skipping.")
            return True

        # 2. Dependency Check
        if not self.validate_dependencies(params):
            return False

        # 3. Clean the params for the API call
        progress_cb = params.pop("progress_cb", None)
        kwargs = params.pop("build_point_cloud", params)

        # 4. Handle Enum String Conversions
        if isinstance(kwargs.get("source_data"), str):
            kwargs["source_data"] = getattr(Metashape, kwargs["source_data"])

        # 5. Build Point Cloud
        self.log(f"Generating Point Cloud with {len(kwargs)} parameters...")
        try:
            self.chunk.buildPointCloud(progress=progress_cb, **kwargs)
        except TypeError as e:
            self.log(f"API Parameter Error in buildPointCloud: {e}. Check your config keys!")
            return False

        # 6. Verify success
        return self.is_completed()