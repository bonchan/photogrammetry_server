import Metashape # type: ignore
from .base import MetashapeTaskBase

class BuildTextureTask(MetashapeTaskBase):

    def is_completed(self) -> bool:
        """Physical check: Does the model already have a texture map?"""
        if not self.chunk or not self.chunk.model:
            return False
        # If the model has a texture list and it's not empty, it's done
        return len(self.chunk.model.textures) > 0

    def validate_dependencies(self) -> bool:
        """
        Dependency Check: Texture requires a 3D Model AND UV mapping to exist first.
        """
        if not self.chunk or not self.chunk.model:
            self.log("Error: No 3D model found. Cannot build texture.")
            return False
        
        if len(self.chunk.model.tex_vertices) == 0:
            self.log("Error: No UV mapping (tex_vertices) found. Build UV before texture.")
            return False
            
        return True

    def run(self, params: dict) -> bool:
        # 1. Idempotency Check
        if self.is_completed():
            self.log("Model texture already exists. Skipping.")
            return True

        # 2. Dependency Check
        if not self.validate_dependencies():
            return False

        # 3. Clean the params for the API call
        progress_cb = params.pop("progress_cb", None)
        kwargs = params.pop("build_texture", params)

        # 4. Handle Enum String Conversions (Safety net for common Enums)
        # Convert strings to actual Metashape objects if passed as text
        if isinstance(kwargs.get("blending_mode"), str):
            kwargs["blending_mode"] = getattr(Metashape, kwargs["blending_mode"])
            
        if isinstance(kwargs.get("texture_type"), str):
            # TextureType lives inside Metashape.Model
            kwargs["texture_type"] = getattr(Metashape.Model, kwargs["texture_type"])

        # 5. Build Texture
        self.log(f"Generating texture with {len(kwargs)} parameters...")
        try:
            self.chunk.buildTexture(progress=progress_cb, **kwargs)
        except TypeError as e:
            self.log(f"API Parameter Error in buildTexture: {e}. Check your JSON keys!")
            return False

        # 6. Verify success
        return self.is_completed()