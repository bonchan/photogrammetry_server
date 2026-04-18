from .base import MetashapeTaskBase

class AlignPhotosTask(MetashapeTaskBase):

    def is_completed(self) -> bool:
        """Physical check: Are there tie points and at least one aligned camera?"""
        if not self.chunk:
            return False
            
        has_tie_points = self.chunk.tie_points is not None
        has_aligned_cameras = any(c.transform for c in self.chunk.cameras if c.transform)
        
        return has_tie_points and has_aligned_cameras

    def validate_dependencies(self) -> bool:
        """Safety check: Do we have what we need to even start?"""
        if not self.chunk or len(self.chunk.cameras) == 0:
            self.log("Error: No cameras in chunk. Cannot align.")
            return False
        return True

    def run(self, params: dict) -> bool:
        # 1. Idempotency Check
        if self.is_completed():
            self.log("Photos are already aligned. Skipping.")
            return True

        # 2. Dependency Check (Calling the method you just added)
        if not self.validate_dependencies():
            return False

        progress_cb = params.get("progress_cb")
        
        # 3. Grab the specific dictionaries from the JSON
        match_kwargs = params.get("match_photos", {})
        align_kwargs = params.get("align_cameras", {})

        # 4. Match Photos
        self.log(f"Matching Photos with {len(match_kwargs)} parameters...")
        try:
            self.chunk.matchPhotos(progress=progress_cb, **match_kwargs)
        except TypeError as e:
            self.log(f"API Error in matchPhotos: {e}. Check your JSON keys!")
            return False

        # 5. Align Cameras
        self.log(f"Aligning Cameras with {len(align_kwargs)} parameters...")
        try:
            self.chunk.alignCameras(progress=progress_cb, **align_kwargs)
        except TypeError as e:
            self.log(f"API Error in alignCameras: {e}. Check your JSON keys!")
            return False

        return self.is_completed()