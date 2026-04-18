import Metashape # type: ignore
from .base import MetashapeTaskBase

class BuildUVTask(MetashapeTaskBase):

    def is_completed(self) -> bool:
        """Physical check: Does the model have texture coordinates (UVs)?"""
        if not self.chunk or not self.chunk.model:
            return False
        # If the model has texture vertices, the UV map is built
        return len(self.chunk.model.tex_vertices) > 0

    def validate_dependencies(self) -> bool:
        """
        Dependency Check: UV mapping requires a 3D Model (Mesh) to exist first.
        """
        if not self.chunk or not self.chunk.model:
            self.log("Error: No 3D model found. Build model before UV.")
            return False
        return True

    def run(self, params: dict) -> bool:
        # 1. Idempotency Check
        if self.is_completed():
            self.log("UV mapping already exists. Skipping.")
            return True

        # 2. Dependency Check
        if not self.validate_dependencies():
            return False

        # 3. Clean the params for the API call
        progress_cb = params.pop("progress_cb", None)
        kwargs = params.pop("build_uv", params)

        # 4. Handle Enum String Conversion (Safety net)
        mapping = kwargs.get("mapping_mode")
        if isinstance(mapping, str):
            self.log(f"Converting string '{mapping}' to Metashape Enum...")
            kwargs["mapping_mode"] = getattr(Metashape, mapping, Metashape.GenericMapping)

        # 5. Build UV
        self.log(f"Generating UV mapping with {len(kwargs)} parameters...")
        try:
            self.chunk.buildUV(progress=progress_cb, **kwargs)
        except TypeError as e:
            self.log(f"API Parameter Error in buildUV: {e}. Check your config keys!")
            return False

        # 6. Verify success
        return self.is_completed()