import os
import json
import urllib.request
import urllib.error
from pathlib import Path
from typing import Dict, Any

# Import the base class (Adjust the import path based on your folder structure)
from .base import MetashapeTaskBase 

class DetectionTask(MetashapeTaskBase):
    """
    WORK IN PROGRESS:
    Delegates ortho-based detection to an external AI Inference Server.
    """

    def is_completed(self) -> bool:
        """Physical check: Does the detections.json exist in the export folder?"""
        export_dir = Path(self.engine.export_path)
        return (export_dir / "detections.json").exists()

    def validate_dependencies(self) -> bool:
        """Requires an Orthomosaic to be present in the exports folder."""
        # Based on engine logic, ortho is exported to a folder named after the dataset
        ortho_folder = Path(self.engine.export_path) / self.engine.expected_files.get("ortho", "")
        
        if not ortho_folder.exists():
            self.log(f"Error: Detection requires Ortho folder at {ortho_folder}")
            return False
        return True

    def run(self, params: Dict[str, Any]) -> bool:
        self.log("--- WORK IN PROGRESS: AI DETECTION TASK ---")
        
        # 1. Dependency Check
        if not self.validate_dependencies():
            return False

        # 2. Locate the KML trace (usually in the input/image folder)
        image_dir = Path(self.engine.input_dir)
        kml_files = list(image_dir.glob("*.kml"))
        
        if not kml_files:
            self.log("No KML file found in input folder. Skipping detection.")
            return self._save_empty_result("No KML available.")

        kml_path = kml_files[0].absolute()
        ortho_path = (Path(self.engine.export_path) / self.engine.expected_files["ortho"]).absolute()

        # 3. Call External Server
        api_url = params.get("api_url", os.getenv("DETECTION_SERVER_URL", "http://localhost:8001/api/detect"))
        
        payload = {
            "dataset_name": self.engine.dataset_name,
            "kml_path": str(kml_path),
            "ortho_path": str(ortho_path),
            "run_inference": True
        }

        try:
            self.log(f"Delegating inference to: {api_url}")
            data = json.dumps(payload).encode('utf-8')
            
            req = urllib.request.Request(
                url=api_url, 
                data=data, 
                headers={'Content-Type': 'application/json'},
                method='POST'
            )
            
            # Timeout set to 1 hour for heavy AI processing
            with urllib.request.urlopen(req, timeout=3600) as response:
                output_data = json.loads(response.read().decode('utf-8'))
            
            # 4. Save results to the engine's export directory
            output_file = Path(self.engine.export_path) / "detections.json"
            with open(output_file, 'w') as f:
                json.dump(output_data, f, indent=2)
                
            self.log("AI Detection successfully completed and saved.")
            return True

        except urllib.error.HTTPError as e:
            self.log(f"AI Server HTTP Error {e.code}: {e.read().decode('utf-8')}")
            return False
        except urllib.error.URLError as e:
            self.log(f"Connection to AI Server failed: {e.reason}")
            return False
        except Exception as e:
            self.log(f"Unexpected error during AI delegation: {e}")
            return False

    def _save_empty_result(self, message: str) -> bool:
        """Saves a failure-state JSON so the UI doesn't hang."""
        self.log(message)
        output_file = Path(self.engine.export_path) / "detections.json"
        empty_data = {
            "dataset": self.engine.dataset_name, 
            "success": False, 
            "message": message,
            "trace": None
        }
        with open(output_file, 'w') as f:
            json.dump(empty_data, f)
        return True