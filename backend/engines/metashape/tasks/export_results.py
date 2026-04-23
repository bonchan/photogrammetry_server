import os
import json
import zipfile
import shutil
import Metashape # type: ignore
from pathlib import Path
from .base import MetashapeTaskBase
from typing import List


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
            self._notify_export_completed("report")

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
            self._notify_export_completed("model")

        # 5. Point Cloud
        if self.chunk.point_cloud and expected.get("point_cloud") and params.get("export_point_cloud", False):
            self.log("Exporting Point Cloud...")
            cloud_path = export_dir / expected["point_cloud"]
            self.chunk.exportPointCloud(path=str(cloud_path), format=Metashape.PointCloudFormatLAS)
            self._notify_export_completed("point_cloud")

        # 6. Raster Outputs (DEM)
        if self.chunk.elevation and expected.get("dem") and params.get("export_dem", False):
            self.log("Exporting DEM...")
            dem_path = export_dir / expected["dem"]
            self.chunk.exportRaster(str(dem_path), source_data=Metashape.ElevationData)
            self._notify_export_completed("dem")


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
            self._notify_export_completed("ortho")

        # 8. Map Tiles (XYZ)
        if self.chunk.orthomosaic and expected.get("map_tiles") and params.get("export_tiles", False):
            self._export_tiles(export_dir, expected["map_tiles"], params)
            self._notify_export_completed("map_tiles")

        # 9. Map Centroid for UI
        self._export_map_center(export_dir)
        self._notify_export_completed("map_center")

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

            tile_meta = {
                "minZoom": params.get("min_zoom", 15),
                "maxZoom": params.get("max_zoom", 22),
                "bounds": self._get_ortho_bounds() # You'll need a helper for this
            }

            with open(os.path.join(extract_dir, "tile_info.json"), 'w') as f:
                json.dump(tile_meta, f)

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

    def _notify_export_completed(self, export_key: str):
        """
        Dynamically appends the finished export to tasks.json 
        so the FastAPI WebSocket instantly lights up the React UI.
        """
        state_file = Path(self.engine.state_file)
        if not state_file.exists():
            return
            
        try:
            with open(state_file, 'r') as f:
                state_data = json.load(f)
            
            # The React UI expects keys like 'export_report', 'export_model'
            ui_key = f"export_{export_key}"
            
            if ui_key not in state_data.get("completed_tasks", []):
                state_data.setdefault("completed_tasks", []).append(ui_key)
                
            # Adding .tmp and replacing prevents file corruption if WS reads mid-write
            temp_file = state_file.with_suffix('.json.tmp')
            with open(temp_file, 'w') as f:
                json.dump(state_data, f)
            os.replace(temp_file, state_file)
            
        except Exception as e:
            self.log(f"Failed to update state file for UI: {e}")

    def _get_ortho_bounds(self) -> List[List[float]]:
        """
        Calculates Lat/Lng bounds for the orthomosaic.
        Returns: [[latMin, lngMin], [latMax, lngMax]]
        """
        ortho = self.chunk.orthomosaic
        crs = self.chunk.crs

        # 1. Get the boundary coordinates in the project's CRS
        # Left/Bottom and Right/Top corners
        pt1 = Metashape.Vector((ortho.left, ortho.bottom))
        pt2 = Metashape.Vector((ortho.right, ortho.top))

        # 2. Transform to WGS84 (Lat/Lng) if the project isn't already
        wgs84 = Metashape.CoordinateSystem("EPSG:4326")
        
        # Helper to transform a 2D point
        def transform_to_latlng(point):
            # Convert 2D to 3D for transformation (adding 0 altitude)
            pt3d = Metashape.Vector((point.x, point.y, 0))
            # Transform from project CRS to WGS84
            res = Metashape.CoordinateSystem.transform(pt3d, crs, wgs84)
            return [res.y, res.x] # Return as [Lat, Lng] for Leaflet

        corner1 = transform_to_latlng(pt1)
        corner2 = transform_to_latlng(pt2)

        # Leaflet expects [[South, West], [North, East]]
        return [corner1, corner2]