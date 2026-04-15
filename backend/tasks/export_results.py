import os
import json
import zipfile
import Metashape # type: ignore
from typing import Dict, Any
from tasks.base_task import BaseTask
from services.metashape_service import MetashapeService
from typing import Dict, Any, List


class ExportResultsTask(BaseTask):
    def validate_dependencies(self) -> bool:
        return self.chunk is not None

    def run(self, params: Dict[str, Any]) -> bool:
        # 1. Setup Naming and Folders via the Service
        # Assuming your SmartWorker has dataset_name. If not, we extract it from the output folder name.
        dataset_name = getattr(self.worker, 'dataset_name', None)
        if not dataset_name:
            basename = os.path.basename(self.worker.output_folder)
            dataset_name = basename.replace("_out", "")

        service = MetashapeService(dataset_name)
        export_dir = service.export_path
        expected = service.expected_files

        if not os.path.exists(export_dir): 
            os.makedirs(export_dir)

        self.log("Starting unified export process...")

        # 2. PDF Report
        if expected.get("report") and params.get("export_report", True):
            self.log("Exporting Report...")
            self.chunk.exportReport(os.path.join(export_dir, expected["report"]))

        # 3. Model Export
        if self.chunk.model and expected.get("model"):
            self.log("Exporting 3D Model...")
            model_path = os.path.join(export_dir, expected["model"])
            
            # Dynamically select format based on the extension defined in the service
            ext = expected["model"].split('.')[-1].lower()
            fmt_map = {
                "obj": Metashape.ModelFormatOBJ, 
                "glb": Metashape.ModelFormatGLTF, 
                "ply": Metashape.ModelFormatPLY
            }
            self.chunk.exportModel(path=model_path, format=fmt_map.get(ext, Metashape.ModelFormatOBJ))

        # 4. Point Cloud
        if self.chunk.point_cloud and expected.get("point_cloud"):
            self.log("Exporting Point Cloud...")
            cloud_path = os.path.join(export_dir, expected["point_cloud"])
            self.chunk.exportPointCloud(path=cloud_path, format=Metashape.PointCloudFormatLAS)

        # 5. Raster Outputs (DEM)
        if self.chunk.elevation and expected.get("dem"):
            self.log("Exporting DEM...")
            self.chunk.exportRaster(os.path.join(export_dir, expected["dem"]), source_data=Metashape.ElevationData)

        # 6. Raster Outputs (Ortho)
        # if self.chunk.orthomosaic and expected.get("ortho"):
        #     self.log("Exporting Orthomosaic...")
        #     self.chunk.exportRaster(os.path.join(export_dir, expected["ortho"]), source_data=Metashape.OrthomosaicData)

        # 7. Map Tiles (XYZ/Leaflet/Mapbox)
        # Note: Since the Service expects "dataset_map_tiles.zip", we just generate the zip 
        # and leave it intact, skipping the extraction and deletion steps from the old code!
        if self.chunk.orthomosaic and expected.get("map_tiles") and params.get("export_tiles", False):
            self.log("Generating XYZ Map Tiles Archive...")
            zip_path = os.path.join(export_dir, expected["map_tiles"])
            
            ortho_proj = Metashape.OrthoProjection()
            ortho_proj.crs = Metashape.CoordinateSystem("EPSG:3857")
            
            self.chunk.exportRaster(
                path=zip_path,
                source_data=Metashape.OrthomosaicData,
                format=Metashape.RasterFormatXYZ,
                image_format=Metashape.ImageFormat.ImageFormatPNG,
                projection=ortho_proj,
                global_profile=True,
                min_zoom_level=params.get("min_zoom", 15),
                max_zoom_level=params.get("max_zoom", 22)
            )

            # Create a folder name by removing '.zip' from the expected filename
            folder_name = expected["map_tiles"].replace(".zip", "")
            extract_dir = os.path.join(export_dir, folder_name)

            if os.path.exists(extract_dir):
                self.log(f"Clearing old tiles from {extract_dir}...")
                import shutil
                shutil.rmtree(extract_dir)
            
            self.log(f"Unzipping map tiles to {extract_dir}...")
            os.makedirs(extract_dir, exist_ok=True)
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)

                tile_meta = {
                    "minZoom": params.get("min_zoom", 15),
                    "maxZoom": params.get("max_zoom", 22),
                    "bounds": self._get_ortho_bounds() # You'll need a helper for this
                }

                with open(os.path.join(extract_dir, "tile_info.json"), 'w') as f:
                  json.dump(tile_meta, f)

        # 8. Map Centroid Calculation (Always run this for the UI map viewer)
        # We save this directly to the export dir as well. You might want to add "map_center.json" to the service later!
        self._export_map_center(export_dir)

        self.log("All exports completed successfully.")
        return True

    def _export_map_center(self, output_folder):
        lats, lngs = [], []
        for cam in self.chunk.cameras:
            if cam.reference and cam.reference.location:
                lngs.append(cam.reference.location[0])
                lats.append(cam.reference.location[1])
        
        if lats and lngs:
            center = {"lat": sum(lats) / len(lats), "lng": sum(lngs) / len(lngs)}
            with open(os.path.join(output_folder, "map_center.json"), 'w') as f:
                json.dump(center, f, indent=2)

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