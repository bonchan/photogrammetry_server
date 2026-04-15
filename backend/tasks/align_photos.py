import Metashape # type: ignore
from typing import Dict, Any, List, Tuple, Optional
from tasks.base_task import BaseTask

class AlignPhotosTask(BaseTask):

    def __init__(self, worker):
        super().__init__(worker)

    def validate_dependencies(self) -> bool:
        if not self.chunk or len(self.chunk.cameras) == 0:
            self.log("Error: No cameras in chunk.")
            return False
        return True

    def run(self, params: Dict[str, Any]) -> bool:
        self.log("Matching Photos (Full API Spec 2.1.2)...")
        return self._match_photos_documented(**params)

    def _match_photos_documented(
        self,
        downscale: int = 1,
        downscale_3d: int = 1,
        generic_preselection: bool = True,
        reference_preselection: bool = True,
        reference_preselection_mode: Metashape.ReferencePreselectionMode = Metashape.ReferencePreselectionSource,
        filter_mask: bool = False,
        mask_tiepoints: bool = True,
        filter_stationary_points: bool = True,
        keypoint_limit: int = 40000,
        keypoint_limit_3d: int = 100000,
        keypoint_limit_per_mpx: int = 1000,
        tiepoint_limit: int = 4000,
        keep_keypoints: bool = False,
        pairs: Optional[List[Tuple[int, int]]] = None,  # Fix 1: Optional None
        cameras: Optional[List[int]] = None,            # Fix 1: Optional None
        guided_matching: bool = False,
        reset_matches: bool = False,
        subdivide_task: bool = True,
        workitem_size_cameras: int = 20,
        workitem_size_pairs: int = 80,
        max_workgroup_size: int = 100,
        laser_scans_vertical_axis: int = 0,
        match_laser_scans: bool = False
    ) -> bool:

        # Fix 2: Build the base kwargs dictionary
        kwargs = {
            "downscale": downscale,
            "downscale_3d": downscale_3d,
            "generic_preselection": generic_preselection,
            "reference_preselection": reference_preselection,
            "reference_preselection_mode": reference_preselection_mode,
            "filter_mask": filter_mask,
            "mask_tiepoints": mask_tiepoints,
            "filter_stationary_points": filter_stationary_points,
            "keypoint_limit": keypoint_limit,
            "keypoint_limit_3d": keypoint_limit_3d,
            "keypoint_limit_per_mpx": keypoint_limit_per_mpx,
            "tiepoint_limit": tiepoint_limit,
            "keep_keypoints": keep_keypoints,
            "guided_matching": guided_matching,
            "reset_matches": reset_matches,
            "subdivide_task": subdivide_task,
            "workitem_size_cameras": workitem_size_cameras,
            "workitem_size_pairs": workitem_size_pairs,
            "max_workgroup_size": max_workgroup_size,
            "laser_scans_vertical_axis": laser_scans_vertical_axis,
            "match_laser_scans": match_laser_scans,
            "progress": self.progress_callback
        }

        # Fix 3: Only inject list parameters if they actually contain data
        if pairs: 
            kwargs["pairs"] = pairs
        if cameras: 
            kwargs["cameras"] = cameras

        # Execute matchPhotos safely
        self.chunk.matchPhotos(**kwargs)

        if self.worker.interrupted: 
            return False

        self.log("Aligning Cameras...")
        self.chunk.alignCameras(
            adaptive_fitting=True,
            subdivide_task=subdivide_task,
            progress=self.progress_callback
        )

        return True