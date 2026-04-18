from .base import MetashapeTaskBase

class BuildDepthMapsTask(MetashapeTaskBase):

    def is_completed(self) -> bool:
        """Physical check: Do depth maps already exist in the chunk?"""
        if not self.chunk:
            return False
        return self.chunk.depth_maps is not None

    def validate_dependencies(self) -> bool:
        """
        Level 3 Dependency: Requires aligned cameras (Level 1).
        """
        if not self.chunk or len(self.chunk.cameras) == 0:
            self.log("Error: No cameras found. Cannot build depth maps.")
            return False
            
        aligned_cameras = [c for c in self.chunk.cameras if c.transform]
        if len(aligned_cameras) < 2:
            self.log(f"Error: At least 2 aligned cameras required. Found {len(aligned_cameras)}.")
            return False
            
        return True

    def run(self, params: dict) -> bool:
        # 1. Idempotency Check
        if self.is_completed():
            self.log("Depth maps already exist. Skipping.")
            return True

        # 2. Dependency Check
        if not self.validate_dependencies():
            return False

        # 3. Clean the params for the API call
        progress_cb = params.pop("progress_cb", None)
        
        # If you decide to nest your JSON just to be consistent with AlignPhotos, 
        # this line safely grabs the nested dict, or defaults to the flat params.
        kwargs = params.pop("build_depth_maps", params)

        # 4. Build Depth Maps
        self.log(f"Generating Depth Maps with {len(kwargs)} custom parameters...")
        try:
            # Blindly pass the JSON parameters to the Metashape C++ engine
            self.chunk.buildDepthMaps(progress=progress_cb, **kwargs)
        except TypeError as e:
            self.log(f"API Parameter Error in buildDepthMaps: {e}. Check your JSON keys!")
            return False

        # 5. Verify success
        return self.is_completed()