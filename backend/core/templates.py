import Metashape # type: ignore
from core.enums import TaskType

PIPELINE_TEMPLATES = {
  "FULL_PROCESS": {
    "label": "Full process",
    "pipeline": [
      TaskType.ADD_PHOTOS, 
      TaskType.ALIGN_PHOTOS,
      TaskType.MODEL,
      TaskType.UV,
      TaskType.TEXTURE,
      TaskType.TILED_MODEL,
      TaskType.POINT_CLOUD,
      TaskType.DEM,
      TaskType.ORTHO,
      TaskType.EXPORT
    ],
    "params": {
      TaskType.ADD_PHOTOS: {
        # "crs": 4326
      },
      TaskType.ALIGN_PHOTOS: {
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
      TaskType.MODEL: {
        # "surface_type": Metashape.Arbitrary,
        # "interpolation": Metashape.EnabledInterpolation,
        # "face_count": Metashape.HighFaceCount,
        # "source_data": Metashape.DepthMapsData,
        # "vertex_colors": True,
        # "volumetric_masks": False,
        # "blocks_crs": Metashape.CoordinateSystem("EPSG::32719"),
      },
      TaskType.UV: {
        # "page_count":2, 
        # "texture_size":4096
      },
      TaskType.TEXTURE: {
        # "texture_size":4096, 
        # "ghosting_filter":True, 
      },
      TaskType.TILED_MODEL: {
      },
      TaskType.POINT_CLOUD: {
      },
      TaskType.DEM: {
      },
      TaskType.ORTHO: {
        # "surface_data": Metashape.ElevationData
      },
      TaskType.EXPORT: {    
        "export_report": True,
        "export_tiles": True,
        "model_format": "obj"
      }
    }
  }
}