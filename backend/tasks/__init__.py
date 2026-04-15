from core.enums import TaskType

from tasks.add_photos import AddPhotosTask
from tasks.align_photos import AlignPhotosTask
from tasks.align_laser_scans import AlignLaserScansTask
from tasks.build_depth_maps import BuildDepthMapsTask
from tasks.build_model import BuildModelTask
from tasks.build_uv import BuildUVTask
from tasks.build_texture import BuildTextureTask
from tasks.build_tiled_model import BuildTiledModelTask
from tasks.build_point_cloud import BuildPointCloudTask
from tasks.build_dem import BuildDemTask
from tasks.build_orthomosaic import BuildOrthomosaicTask
from tasks.export_results import ExportResultsTask
from tasks.cleanup import CleanupTask

# This map connects the Enum/String from the DB to the actual Code
TASK_REGISTRY = {
  TaskType.ADD_PHOTOS: AddPhotosTask,
  TaskType.ALIGN_PHOTOS: AlignPhotosTask,
  TaskType.ALIGNMENT_LASER_SCANS: AlignLaserScansTask,
  TaskType.DEPTH_MAPS: BuildDepthMapsTask,
  TaskType.MODEL: BuildModelTask,
  TaskType.UV: BuildUVTask,
  TaskType.TEXTURE: BuildTextureTask,
  TaskType.TILED_MODEL: BuildTiledModelTask,
  TaskType.POINT_CLOUD: BuildPointCloudTask,
  TaskType.DEM: BuildDemTask,
  TaskType.ORTHO: BuildOrthomosaicTask,
  TaskType.EXPORT: ExportResultsTask,
  TaskType.CLEANUP: CleanupTask,
}