from .base import MetashapeTaskBase

class BuildModelTask(MetashapeTaskBase):

    def is_completed(self) -> bool:
        """Physical check: Does a 3D mesh model already exist in the chunk?"""
        if not self.chunk:
            return False
        return self.chunk.model is not None

    def validate_dependencies(self, params: dict) -> bool:
        """
        Dynamically checks for the correct source data based on the JSON config.
        """
        if not self.chunk:
            return False

        # Metashape 2.x defaults to using Depth Maps (Enum value 4)
        # 0 = TiePoints, 1 = PointCloud (formerly DenseCloud), 4 = DepthMaps, 5 = LaserScans
        source_data = params.get("source_data", 4)

        if source_data == 0 and not self.chunk.tie_points:
            self.log("Error: Source set to Tie Points, but none exist.")
            return False
        elif source_data == 1 and not self.chunk.point_cloud:
            self.log("Error: Source set to Point Cloud, but none exists.")
            return False
        elif source_data == 4 and not self.chunk.depth_maps:
            self.log("Error: Source set to Depth Maps, but none exist.")
            return False
            
        return True

    def run(self, params: dict) -> bool:
        # 1. Idempotency Check
        if self.is_completed():
            self.log("3D Mesh Model already exists. Skipping.")
            return True

        # 2. Dependency Check (Notice we pass params into it now!)
        if not self.validate_dependencies(params):
            return False

        # 3. Clean the params for the API call
        progress_cb = params.pop("progress_cb", None)
        
        # Support both nested JSON ("build_model": {...}) and flat JSON
        kwargs = params.pop("build_model", params)

        # 4. Build Model
        self.log(f"Generating 3D Mesh Model with {len(kwargs)} custom parameters...")
        try:
            self.chunk.buildModel(progress=progress_cb, **kwargs)
        except TypeError as e:
            self.log(f"API Parameter Error in buildModel: {e}. Check your JSON keys!")
            return False

        # 5. Verify success
        return self.is_completed()