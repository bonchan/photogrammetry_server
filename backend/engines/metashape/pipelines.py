from .enums import MetashapeTask

METASHAPE_PIPELINES = {
    "inspection": {
        "name": "Asset Inspection (3D)",
        "description": "High-res textured 3D model for welds and pipes.",
        "tasks": [
            MetashapeTask.ADD_PHOTOS,
            MetashapeTask.ALIGN_PHOTOS,
            MetashapeTask.DEPTH_MAPS,
            MetashapeTask.MODEL,
            MetashapeTask.UV,
            MetashapeTask.TEXTURE,
            MetashapeTask.EXPORT,
        ],
        "required_asset": "texture" # The 'Goal' asset
    },
    "volumetry": {
        "name": "Earthworks & Volumetry",
        "tasks": [
            MetashapeTask.ADD_PHOTOS,
            MetashapeTask.ALIGN_PHOTOS,
            MetashapeTask.DEPTH_MAPS,
            MetashapeTask.DEM,
            MetashapeTask.EXPORT,
        ],
        "required_asset": "dem"
    },
    "mapping": {
        "name": "Site Mapping (2D)",
        "tasks": [
            MetashapeTask.ADD_PHOTOS,
            MetashapeTask.ALIGN_PHOTOS,
            MetashapeTask.DEPTH_MAPS,
            MetashapeTask.DEM,
            MetashapeTask.ORTHO,
            MetashapeTask.EXPORT,
        ],
        "required_asset": "ortho"
    },
    "tiled_model": {
        "name": "Map Tiles",
        "tasks": [
            MetashapeTask.ADD_PHOTOS,
            MetashapeTask.ALIGN_PHOTOS,
            MetashapeTask.DEPTH_MAPS,
            MetashapeTask.MODEL,
            MetashapeTask.UV,
            MetashapeTask.TEXTURE,
            MetashapeTask.TILED_MODEL,
            MetashapeTask.POINT_CLOUD,
            MetashapeTask.DEM,
            MetashapeTask.ORTHO,
            MetashapeTask.EXPORT,
            # MetashapeTask.DETECTION,
        ],
        "required_asset": "ortho"
    },
    "point_cloud": {
        "name": "Dense Point Cloud",
        "tasks": [
            MetashapeTask.ADD_PHOTOS,
            MetashapeTask.ALIGN_PHOTOS,
            MetashapeTask.DEPTH_MAPS,
            MetashapeTask.POINT_CLOUD,
            MetashapeTask.EXPORT,
        ],
        "required_asset": "point_cloud"
    },
    "panorama": {
        "name": "360 Panorama Build",
        "tasks": [
            MetashapeTask.ADD_PHOTOS,
            MetashapeTask.ALIGN_PHOTOS,
            MetashapeTask.DEPTH_MAPS,
            MetashapeTask.ORTHO,
            MetashapeTask.EXPORT,
        ],
        "required_asset": "panorama"
    }
}