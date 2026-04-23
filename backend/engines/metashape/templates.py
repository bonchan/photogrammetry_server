from .enums import MetashapeTask

# TODO: Move these templates to the database as JSON objects.
# For now, keeping them here as primitive dictionaries (No Metashape objects!)

METASHAPE_TEMPLATES = {
  "FULL_PROCESS": {
    "label": "Full process",
    "params": {
      MetashapeTask.ADD_PHOTOS: {
        # "crs": 4326
      },
      MetashapeTask.ALIGN_PHOTOS: {
        # "downscale": 1,
        # "generic_preselection": True,
        # "reference_preselection": True,
        # "filter_mask": False,
        # "mask_tiepoints": False,
        # "filter_stationary_points": True,
        # "keypoint_limit": 60000,
        # "keypoint_limit_per_mpx": 1000,
        # "tiepoint_limit": 0,
        # "guided_matching": False,
      },
      MetashapeTask.DEPTH_MAPS: {
      },
      
      MetashapeTask.MODEL: {
        # "surface_type": Metashape.Arbitrary,
        # "interpolation": Metashape.EnabledInterpolation,
        # "face_count": Metashape.HighFaceCount,
        # "source_data": Metashape.DepthMapsData,
        # "vertex_colors": True,
        # "volumetric_masks": False,
        # "blocks_crs": Metashape.CoordinateSystem("EPSG::32719"),
      },
      MetashapeTask.UV: {
        # "page_count":2, 
        # "texture_size":4096
      },
      MetashapeTask.TEXTURE: {
        # "texture_size":4096, 
        # "ghosting_filter":True, 
      },
      MetashapeTask.TILED_MODEL: {
      },
      MetashapeTask.POINT_CLOUD: {
      },
      MetashapeTask.DEM: {
      },
      MetashapeTask.ORTHO: {
        # "surface_data": Metashape.ElevationData

      },
      MetashapeTask.EXPORT: {    
        "export_report": True,
        "export_model": False,
        "export_point_cloud": False,
        "export_dem": False,
        "export_ortho": True,
        "export_tiles": True
      },
      MetashapeTask.DETECTION: {
        
      },
    }
  }
}