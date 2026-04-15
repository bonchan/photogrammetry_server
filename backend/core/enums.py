from enum import Enum

class JobStatus(str, Enum):
  PENDING = "PENDING"
  PROCESSING = "PROCESSING"
  COMPLETED = "COMPLETED"
  FAILED = "FAILED"
  CANCELLED = "CANCELLED"

class StepStatus(str, Enum):
  PENDING = "PENDING"
  RUNNING = "RUNNING"
  SUCCESS = "SUCCESS"
  FAILED = "FAILED"
  SKIPPED = "SKIPPED"

class TaskType(str, Enum):
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
  EXPORT = "export"
  CLEANUP = "cleanup"