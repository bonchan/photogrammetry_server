import sys
import os
import zipfile
import json

# Get the directory where worker.py lives (which is the backend folder)
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

import Metashape
from database import update_job_status

# 1. Compatibility Check (Keep your strict logic)
compatible_major_version = "2.1"
found_major_version = ".".join(Metashape.app.version.split('.')[:2])
if found_major_version != compatible_major_version:
    raise Exception(f"Incompatible Metashape version: {found_major_version} != {compatible_major_version}")

def find_files(folder, types):
    return [entry.path for entry in os.scandir(folder) if (entry.is_file() and os.path.splitext(entry.name)[1].lower() in types)]

def main():
    # Expecting: worker.py <image_folder> <output_folder> <job_id>
    if len(sys.argv) < 4:
        print("Usage: worker.py <image_folder> <output_folder> <job_id>")
        sys.exit(1)

    image_folder = sys.argv[1]
    output_folder = sys.argv[2]
    job_id = int(sys.argv[3])

    # Ensure output directory exists
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Progress Callback wrapper
    def progress_callback(p):
        update_job_status(job_id, progress=round(p, 1))

    try:
        update_job_status(job_id, status="PROCESSING", step="Finding Files")
        photos = find_files(image_folder, [".jpg", ".jpeg", ".tif", ".tiff"])

        if not photos:
            raise Exception("No photos found in the specified directory.")

        doc = Metashape.Document()
        doc.save(os.path.join(output_folder, 'project.psx'))

        chunk = doc.addChunk()
        chunk.addPhotos(photos)
        doc.save()
        
        update_job_status(job_id, step=f"Loaded {len(chunk.cameras)} images")

        # Alignment
        update_job_status(job_id, step="Matching Photos")
        chunk.matchPhotos(keypoint_limit=40000, tiepoint_limit=10000, 
                          generic_preselection=True, reference_preselection=True, 
                          progress=progress_callback)
        doc.save()

        update_job_status(job_id, step="Aligning Cameras")
        chunk.alignCameras(progress=progress_callback)
        doc.save()

        # Depth Maps & Mesh
        update_job_status(job_id, step="Building Depth Maps")
        chunk.buildDepthMaps(downscale=2, filter_mode=Metashape.MildFiltering, progress=progress_callback)
        doc.save()

        update_job_status(job_id, step="Building Model")
        chunk.buildModel(source_data=Metashape.DepthMapsData, progress=progress_callback)
        doc.save()

        # UV & Texture
        update_job_status(job_id, step="Building Texture")
        chunk.buildUV(page_count=2, texture_size=4096)
        chunk.buildTexture(texture_size=4096, ghosting_filter=True, progress=progress_callback)
        doc.save()

        # Georeferencing Check
        has_transform = chunk.transform.scale and chunk.transform.rotation and chunk.transform.translation
        if has_transform:
            # update_job_status(job_id, step="Building Point Cloud (Georeferenced)")
            # chunk.buildPointCloud(progress=progress_callback)
            # doc.save()

            # update_job_status(job_id, step="Building DEM")
            # chunk.buildDem(source_data=Metashape.PointCloudData, progress=progress_callback)
            # doc.save()

            update_job_status(job_id, step="Building Orthomosaic")
            chunk.buildOrthomosaic(surface_data=Metashape.ElevationData, progress=progress_callback)
            doc.save()

        # Export Results
        update_job_status(job_id, step="Exporting Reports and Assets")
        chunk.exportReport(os.path.join(output_folder, 'report.pdf'))

        # if chunk.model:
        #     chunk.exportModel(os.path.join(output_folder, 'model.obj'))
            
            # update_job_status(job_id, step="Decimating Model for WebGL")
            # chunk.decimateModel(face_count=200000, progress=progress_callback)
            # doc.save()
            
            # update_job_status(job_id, step="Baking WebGL Textures")
            # chunk.buildUV(page_count=1, texture_size=4096) 
            # chunk.buildTexture(texture_size=4096, ghosting_filter=True, progress=progress_callback)
            # doc.save()
            
            # # 3. Export the low-poly version (Now it will have a proper .mtl and .jpg!)
            # chunk.exportModel(os.path.join(output_folder, 'model_decimated.obj'))

        # if chunk.point_cloud:
        #     chunk.exportPointCloud(os.path.join(output_folder, 'point_cloud.las'), source_data=Metashape.PointCloudData)

        if chunk.elevation:
            chunk.exportRaster(os.path.join(output_folder, 'dem.tif'), source_data=Metashape.ElevationData)

        if chunk.orthomosaic:
            chunk.exportRaster(os.path.join(output_folder, 'orthomosaic.tif'), source_data=Metashape.OrthomosaicData)
            
            chunk.exportRaster(
                path=os.path.join(output_folder, 'orthophoto_preview.jpg'),
                source_data=Metashape.OrthomosaicData,
                image_format=Metashape.ImageFormat.ImageFormatJPEG,
            )

        if chunk.orthomosaic:
            update_job_status(job_id, step="Exporting Map Tiles")
            
            zip_path = os.path.join(output_folder, "tiles.zip")
            
            # 1. The Geographic Projection (Forces zoom levels 15+ instead of 0-5)
            ortho_proj = Metashape.OrthoProjection()
            ortho_proj.crs = Metashape.CoordinateSystem("EPSG:3857")
            
            chunk.exportRaster(
                path=zip_path,
                source_data=Metashape.OrthomosaicData,
                format=Metashape.RasterFormatXYZ,
                image_format=Metashape.ImageFormat.ImageFormatPNG,
                projection=ortho_proj,
                global_profile=True,
                min_zoom_level=15,
                max_zoom_level=22,
                clip_to_boundary=False,
                save_alpha=True,
                white_background=False
            )

            # 2026-04-11 10:14:10 ExportOrthomosaic: 
            # path = C:/code/photogrammetry_server/outputs/asdsd.zip, 
            # format = RasterFormatXYZ, 
            # image_format = PNG, 
            # projection = WGS 84 / Pseudo-Mercator, 
            # resolution_x = 0.037322800000000003, 
            # resolution_y = 0.037322800000000003, 
            # global_profile = on, 
            # min_zoom_level = 15, 
            # max_zoom_level = 22, 
            # clip_to_boundary = off, 
            # asset = 0

            # 3. Extract the folders
            update_job_status(job_id, step="Extracting Tiles")
            tile_dir = os.path.join(output_folder, 'tiles')
            
            if not os.path.exists(tile_dir):
                os.makedirs(tile_dir)
                
            import zipfile
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(tile_dir)

            os.remove(zip_path)

        # --- START CENTROID CALCULATION ---
        update_job_status(job_id, step="Calculating Map Center")
        lats = []
        lngs = []
        for camera in chunk.cameras:
            # Ensure the camera has reference data and a location
            if camera.reference and camera.reference.location:
                # Metashape location vector is [Longitude, Latitude, Altitude]
                lngs.append(camera.reference.location[0])
                lats.append(camera.reference.location[1])
                
        if lats and lngs:
            # Calculate the exact center (average) of all photos
            center_data = {
                "lat": sum(lats) / len(lats),
                "lng": sum(lngs) / len(lngs)
            }
            
            # Save it alongside your tiles and orthomosaic
            json_path = os.path.join(output_folder, "map_center.json")
            with open(json_path, 'w') as f:
                json.dump(center_data, f, indent=2)
                
            print(f"Successfully saved map_center.json at {center_data['lat']}, {center_data['lng']}")
        else:
            print("WARNING: No GPS data found in cameras. map_center.json was not created.")
        # --- END CENTROID CALCULATION ---

        update_job_status(job_id, status="COMPLETED", step="Finished", progress=100.0)

    except Exception as e:
        print(f"Error: {str(e)}")
        update_job_status(job_id, status="FAILED", step=str(e)[:200]) # Truncate error if too long

if __name__ == "__main__":
    main()