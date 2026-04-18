from enum import Enum

class MetashapeTask(str, Enum):
  ADD_PHOTOS = "add_photos"
  ALIGN_PHOTOS = "align_photos"
  ALIGNMENT_LASER_SCANS = "alignment_laser_scans"
  DEPTH_MAPS = "depth_maps"
  MODEL = "model"
  UV = "uv"
  TEXTURE = "texture"
  TILED_MODEL = "tiled_model"
  POINT_CLOUD = "point_cloud"
  DEM = "dem"
  ORTHO = "ortho"
  DETECTION = "detection"
  EXPORT = "export"
  CLEANUP = "cleanup"