import os
import json
import zipfile
import shutil
import Metashape # type: ignore
from pathlib import Path
from .base import MetashapeTaskBase

class ExportResultsTask(MetashapeTaskBase):

    def is_completed(self) -> bool:
        # Export is a "force run" task in most pipelines
        return False

    def validate_dependencies(self) -> bool:
        return self.chunk is not None

    def run(self, params: dict) -> bool:
        # 1. Setup Naming and Folders from Engine
        export_dir = Path(self.engine.export_path)
        expected = self.engine.expected_files
        
        # 2. Ruthless Reset: Delete and recreate the export folder
        # This handles the TIF blocks issue (clearing old pieces)
        if export_dir.exists():
            self.log(f"Clearing existing export directory: {export_dir}")
            shutil.rmtree(export_dir)
        
        export_dir.mkdir(parents=True, exist_ok=True)
        self.log(f"Starting export to {export_dir}...")

        # 3. PDF Report
        if expected.get("report") and params.get("export_report", True):
            self.log("Exporting Report...")
            self.chunk.exportReport(str(export_dir / expected["report"]))

        # 4. 3D Model Export
        if self.chunk.model and expected.get("model") and params.get("export_model", False):
            self.log("Exporting 3D Model...")
            model_path = export_dir / expected["model"]
            ext = model_path.suffix.lower().replace('.', '')
            
            fmt_map = {
                "obj": Metashape.ModelFormatOBJ, 
                "glb": Metashape.ModelFormatGLTF, 
                "ply": Metashape.ModelFormatPLY
            }
            
            self.chunk.exportModel(
                path=str(model_path), 
                format=fmt_map.get(ext, Metashape.ModelFormatOBJ),
                save_texture=True,
                save_uv=True,
                texture_format=Metashape.ImageFormatJPEG
            )

        # 5. Point Cloud
        if self.chunk.point_cloud and expected.get("point_cloud") and params.get("export_point_cloud", False):
            self.log("Exporting Point Cloud...")
            cloud_path = export_dir / expected["point_cloud"]
            self.chunk.exportPointCloud(path=str(cloud_path), format=Metashape.PointCloudFormatLAS)

        # 6. Raster Outputs (DEM)
        if self.chunk.elevation and expected.get("dem") and params.get("export_dem", False):
            self.log("Exporting DEM...")
            dem_path = export_dir / expected["dem"]
            self.chunk.exportRaster(str(dem_path), source_data=Metashape.ElevationData)

        # 7. Raster Outputs (Ortho) - Handles Single TIF or Blocks
        if self.chunk.orthomosaic and expected.get("ortho") and params.get("export_ortho", False):
            self.log("Exporting Orthomosaic to folder...")
            
            # Create the dedicated ortho folder inside the export directory
            ortho_folder = export_dir / expected["ortho"]
            ortho_folder.mkdir(parents=True, exist_ok=True)

            # We define the filename inside that folder. 
            # Metashape will append suffixes to this for blocks (e.g. ortho_1_1.tif)
            ortho_output_path = ortho_folder / f"{self.engine.dataset_name}_ortho.tif"

            comp = Metashape.ImageCompression()
            comp.tiff_compression = Metashape.ImageCompression.TiffCompressionLZW

            self.chunk.exportRaster(
                path=str(ortho_output_path),
                source_data=Metashape.OrthomosaicData,
                split_in_blocks=params.get("split_in_blocks", True),
                block_width=params.get("block_size", 8192),
                block_height=params.get("block_size", 8192),
                save_alpha=False,
                image_compression=comp
            )

        # 8. Map Tiles (XYZ)
        if self.chunk.orthomosaic and expected.get("map_tiles") and params.get("export_tiles", False):
            self._export_tiles(export_dir, expected["map_tiles"], params)

        # 9. Map Centroid for UI
        self._export_map_center(export_dir)

        self.log("All exports completed successfully.")
        return True

    def _export_tiles(self, export_dir: Path, zip_name: str, params: dict):
        self.log("Generating XYZ Map Tiles Archive...")
        zip_path = export_dir / zip_name
        
        ortho_proj = Metashape.OrthoProjection()
        ortho_proj.crs = Metashape.CoordinateSystem("EPSG:3857")
        
        self.chunk.exportRaster(
            path=str(zip_path),
            source_data=Metashape.OrthomosaicData,
            format=Metashape.RasterFormatXYZ,
            image_format=Metashape.ImageFormatPNG,
            projection=ortho_proj,
            global_profile=True,
            min_zoom_level=params.get("min_zoom", 15),
            max_zoom_level=params.get("max_zoom", 22)
        )
        
        # Unzip for UI if requested
        extract_dir = export_dir / zip_name.replace(".zip", "")
        extract_dir.mkdir(exist_ok=True)
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)

    def _export_map_center(self, export_dir: Path):
        lats, lngs = [], []
        for cam in self.chunk.cameras:
            if cam.reference and cam.reference.location:
                lngs.append(cam.reference.location[0])
                lats.append(cam.reference.location[1])
        
        if lats and lngs:
            center = {"lat": sum(lats)/len(lats), "lng": sum(lngs)/len(lngs)}
            with open(export_dir / "map_center.json", 'w') as f:
                json.dump(center, f, indent=2)