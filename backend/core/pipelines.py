from core.enums import TaskType

PIPELINE_PROFILES = {
    "inspection": {
        "name": "Asset Inspection (3D)",
        "description": "High-res textured 3D model for welds and pipes.",
        "tasks": [
            TaskType.ADD_PHOTOS,
            TaskType.ALIGN_PHOTOS,
            TaskType.DEPTH_MAPS,
            TaskType.MODEL,
            TaskType.UV,
            TaskType.TEXTURE,
            TaskType.EXPORT,
        ],
        "required_asset": "texture" # The 'Goal' asset
    },
    "volumetry": {
        "name": "Earthworks & Volumetry",
        "tasks": [
            TaskType.ADD_PHOTOS,
            TaskType.ALIGN_PHOTOS,
            TaskType.DEPTH_MAPS,
            TaskType.DEM,
            TaskType.EXPORT,
        ],
        "required_asset": "dem"
    },
    "mapping": {
        "name": "Site Mapping (2D)",
        "tasks": [
            TaskType.ADD_PHOTOS,
            TaskType.ALIGN_PHOTOS,
            TaskType.DEPTH_MAPS,
            TaskType.DEM,
            TaskType.ORTHO,
            TaskType.EXPORT,
        ],
        "required_asset": "ortho"
    },
    "tiled_model": {
        "name": "Map Tiles",
        "tasks": [
            TaskType.ADD_PHOTOS,
            TaskType.ALIGN_PHOTOS,
            TaskType.DEPTH_MAPS,
            TaskType.MODEL,
            TaskType.UV,
            TaskType.TEXTURE,
            # TaskType.TILED_MODEL,
            TaskType.POINT_CLOUD,
            TaskType.DEM,
            TaskType.ORTHO,
            TaskType.EXPORT,
            # TaskType.DETECTION,
        ],
        "required_asset": "ortho"
    },
    "point_cloud": {
        "name": "Dense Point Cloud",
        "tasks": [
            TaskType.ADD_PHOTOS,
            TaskType.ALIGN_PHOTOS,
            TaskType.DEPTH_MAPS,
            TaskType.POINT_CLOUD,
            TaskType.EXPORT,
        ],
        "required_asset": "point_cloud"
    },
    "panorama": {
        "name": "360 Panorama Build",
        "tasks": [
            TaskType.ADD_PHOTOS,
            TaskType.ALIGN_PHOTOS,
            TaskType.DEPTH_MAPS,
            TaskType.ORTHO,
            TaskType.EXPORT,
        ],
        "required_asset": "panorama"
    }
}