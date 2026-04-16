import os
import json
import urllib.request
import urllib.error
from tasks.base_task import BaseTask

class DetectionTask(BaseTask):
    def run(self, params: dict) -> bool:
        self.log("Delegating Detection to External AI Server...")
        return True
        
        # 1. Locate the KML trace
        kml_files = [f for f in os.listdir(self.worker.image_folder) if f.lower().endswith('.kml')]
        if not kml_files:
            return False #self._save_empty_result("No KML file found. Skipping detection.")
        
        # We need absolute paths so the external server can find them on the disk
        kml_path = os.path.abspath(os.path.join(self.worker.image_folder, kml_files[0]))
        
        # 2. Locate the Ortho Folder
        # Based on your expected_files, this is a directory, not a single file
        ortho_folder_name = f"{self.worker.dataset_name}_ortho"
        ortho_path = os.path.abspath(os.path.join(self.worker.output_folder, "exports", ortho_folder_name))
        
        if not os.path.exists(ortho_path):
            self.log(f"Error: Ortho folder not found at {ortho_path}")
            return False

        # 3. Call the External Detection Server
        # You can pass this via an environment variable later, defaulting to a local port
        detection_api_url = os.getenv("DETECTION_SERVER_URL", "http://localhost:8001/api/detect")
        
        payload = {
            "dataset_name": self.worker.dataset_name,
            "kml_path": kml_path,
            "ortho_path": ortho_path,
            "run_inference": True
        }

        try:
            self.log(f"Sending AI request to: {detection_api_url}")
            
            # Convert payload to JSON bytes
            data = json.dumps(payload).encode('utf-8')
            
            # Create the Request object
            req = urllib.request.Request(
                url=detection_api_url, 
                data=data, 
                headers={'Content-Type': 'application/json'},
                method='POST'
            )
            
            # Send request (timeout = 3600 seconds)
            with urllib.request.urlopen(req, timeout=3600) as response:
                response_body = response.read().decode('utf-8')
                output_data = json.loads(response_body)
            
            # 4. Save the returned JSON from the AI server
            export_path = os.path.join(self.worker.output_folder, "exports", "detections.json")
            os.makedirs(os.path.dirname(export_path), exist_ok=True)
            
            with open(export_path, 'w') as f:
                json.dump(output_data, f, indent=2)
                
            self.log("Successfully received and saved detections from AI Server.")
            return True

        except urllib.error.HTTPError as e:
            # Handles 404, 500, etc.
            error_msg = e.read().decode('utf-8')
            self.log(f"AI Server returned HTTP Error {e.code}: {error_msg}")
            return False
        except urllib.error.URLError as e:
            # Handles connection refused (server not running)
            self.log(f"Failed to reach Detection Server: {e.reason}")
            return False
        except Exception as e:
            self.log(f"Unexpected error during AI delegation: {str(e)}")
            return False

    def _save_empty_result(self, message) -> bool:
        self.log(message)
        export_path = os.path.join(self.worker.output_folder, "exports", "detections.json")
        os.makedirs(os.path.dirname(export_path), exist_ok=True)
        with open(export_path, 'w') as f:
            json.dump({"dataset": self.worker.current_task_name, "success": False, "trace": None}, f)
        return True
    
    
    
    
    
    
    
    
# import os
# import json
# import math
# import random
# import xml.etree.ElementTree as ET
# from tasks.base_task import BaseTask

# class DetectionTask(BaseTask):
#     # Colors and offsets for the ribbon
#     PROCESS_STATES = [
#         {"name": "Clearing",       "offset": 0.00010, "color": "#ffeb3b", "level": 1},
#         {"name": "Trenching",      "offset": 0.00020, "color": "#ff9800", "level": 2},
#         {"name": "Pipe Dropped",   "offset": 0.00030, "color": "#9c27b0", "level": 3},
#         {"name": "Backfilled",     "offset": 0.00040, "color": "#4caf50", "level": 4}
#     ]

#     def run(self, params: dict) -> bool:
#         self.log("Generating Randomized Linear Progress Ribbon...")
#         return True
        
#         kml_files = [f for f in os.listdir(self.worker.image_folder) if f.lower().endswith('.kml')]
#         if not kml_files: return False
        
#         kml_path = os.path.join(self.worker.image_folder, kml_files[0])
        
#         try:
#             tree = ET.parse(kml_path)
#             root = tree.getroot()
#             ns = {'kml': 'http://www.opengis.net/kml/2.2'}
            
#             # 1. Extract Base Line Points
#             base_points = []
#             for placemark in root.findall('.//kml:Placemark', ns):
#                 ls = placemark.find('.//kml:LineString', ns)
#                 if ls is not None:
#                     coords = ls.find('kml:coordinates', ns).text.strip().split()
#                     for c in coords:
#                         lon, lat, *_ = map(float, c.split(','))
#                         base_points.append((lon, lat))
#                     break # Only process first linestring found

#             if not base_points: return False

#             features = []
#             # Totals in meters (approx)
#             state_totals = {s["name"]: 0.0 for s in self.PROCESS_STATES}
#             total_project_length = 0.0

#             # 2. Process Line in segments
#             for i in range(len(base_points) - 1):
#                 p1 = base_points[i]
#                 p2 = base_points[i+1]
                
#                 # Calculate segment distance (Euclidean approx for logic)
#                 dist = math.sqrt((p2[0]-p1[0])**2 + (p2[1]-p1[1])**2)
#                 # Approx degree to meters (very rough, usually ~111,000m per degree)
#                 segment_meters = dist * 111320 
#                 total_project_length += segment_meters

#                 # Assign a RANDOM current progress level for this segment (0 to 4)
#                 current_level = random.randint(0, len(self.PROCESS_STATES))

#                 # For every state up to the current level, draw a parallel segment
#                 for state_idx in range(current_level):
#                     state = self.PROCESS_STATES[state_idx]
                    
#                     # Offset this specific segment
#                     offset_seg = self._offset_segment(p1, p2, state["offset"])
                    
#                     features.append({
#                         "type": "Feature",
#                         "properties": {
#                             "state": state["name"],
#                             "color": state["color"],
#                             "type": "progress_ribbon"
#                         },
#                         "geometry": {
#                             "type": "LineString",
#                             "coordinates": offset_seg
#                         }
#                     })
#                     # Update totals
#                     state_totals[state["name"]] += segment_meters

#             # 3. Final Output
#             output_data = {
#                 "dataset": self.worker.current_task_name,
#                 "success": True,
#                 "summary": {
#                     "total_meters": round(total_project_length, 2),
#                     "states": [
#                         {
#                             "name": name, 
#                             "meters": round(m, 2), 
#                             "percent": round((m/total_project_length)*100, 1) if total_project_length > 0 else 0
#                         }
#                         for name, m in state_totals.items()
#                     ]
#                 },
#                 "trace": {"type": "FeatureCollection", "features": features}
#             }

#             export_path = os.path.join(self.worker.output_folder, "exports", "detections.json")
#             with open(export_path, 'w') as f:
#                 json.dump(output_data, f, indent=2)

#             return True

#         except Exception as e:
#             self.log(f"Ribbon generation failed: {str(e)}")
#             return False

#     def _offset_segment(self, p1, p2, distance):
#         """Returns the two points of a segment offset by distance."""
#         dx = p2[0] - p1[0]
#         dy = p2[1] - p1[1]
#         mag = math.sqrt(dx**2 + dy**2)
#         if mag == 0: return [list(p1), list(p2)]

#         # Perpendicular vector
#         nx = -dy / mag
#         ny = dx / mag

#         return [
#             [p1[0] + nx * distance, p1[1] + ny * distance],
#             [p2[0] + nx * distance, p2[1] + ny * distance]
#         ]