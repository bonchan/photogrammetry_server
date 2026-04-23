import os
import glob
import math
import uuid
import json
import cv2
import numpy as np
import rasterio
from rasterio.windows import Window
import xml.etree.ElementTree as ET
from osgeo import gdal
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import time
import supervision as sv
import shutil

gdal.PushErrorHandler('CPLQuietErrorHandler')

app = FastAPI(title="Pipeline AI Detection Server")

# --- Configuration & Global State ---
WEIGHTS_PATH = r"C:\code\rfdetr\datasets\003_oilpipe_ortho_tagged\results\checkpoint_best_ema.pth"
CUSTOM_CLASSES = ["pipe", "pipewelded", "trench", "pipelowered"]

STEP_METERS = 50

model = None 

PROCESS_STATES = [
    {"name": "Trenching",    "class": "trench",      "offset": 0.00010, "color": "#ff9800"}, 
    {"name": "Pipe Dropped", "class": "pipe",        "offset": 0.00020, "color": "#9c27b0"},
    {"name": "Pipe Welded",  "class": "pipewelded",  "offset": 0.00030, "color": "#f44336"},
    {"name": "Pipe Lowered", "class": "pipelowered", "offset": 0.00040, "color": "#2196f3"}
]

class DetectionRequest(BaseModel):
    dataset_name: str
    kml_path: str
    ortho_path: str
    run_inference: bool = True 

def get_model():
    global model
    if model is None:
        print(f"\n[AI] Initializing Model: Loading weights from {WEIGHTS_PATH}...")
        from rfdetr import RFDETRBase 
        if os.path.exists(WEIGHTS_PATH):
            print(f'WEIGHTS_PATH {WEIGHTS_PATH}')
            time.sleep(5)
            model = RFDETRBase(pretrain_weights=WEIGHTS_PATH, num_classes=len(CUSTOM_CLASSES))
            print("[AI] Model loaded successfully into VRAM.")
        else:
            print(f"[ERROR] Weights missing at {WEIGHTS_PATH}!")
            raise RuntimeError(f"Weights not found at {WEIGHTS_PATH}")
    return model

def offset_segment(p1, p2, distance):
    dx, dy = p2[0] - p1[0], p2[1] - p1[1]
    mag = math.sqrt(dx**2 + dy**2)
    if mag == 0: return [list(p1), list(p2)]
    nx, ny = -dy / mag, dx / mag
    return [[p1[0] + nx * distance, p1[1] + ny * distance], [p2[0] + nx * distance, p2[1] + ny * distance]]


def resample_trace(points, step_meters=100):
    """
    Takes a list of (lon, lat) points and returns a new list of points
    spaced exactly 'step_meters' apart along the path.
    """
    if len(points) < 2:
        return points

    # Convert approx meters back to degrees for the math
    # 111320 meters approx 1 degree
    step_degrees = step_meters / 111320
    
    new_points = [points[0]]
    leftover = 0
    
    for i in range(len(points) - 1):
        p1 = np.array(points[i])
        p2 = np.array(points[i+1])
        
        vector = p2 - p1
        dist = np.linalg.norm(vector)
        
        if dist + leftover < step_degrees:
            leftover += dist
            continue
            
        # Direction vector
        unit_vector = vector / dist
        
        # Calculate first point on this segment
        current_pos = p1 + unit_vector * (step_degrees - leftover)
        new_points.append(tuple(current_pos))
        
        # Calculate subsequent points on this same segment
        remaining_dist = dist - (step_degrees - leftover)
        while remaining_dist >= step_degrees:
            current_pos += unit_vector * step_degrees
            new_points.append(tuple(current_pos))
            remaining_dist -= step_degrees
            
        leftover = remaining_dist
        
    # Always include the very last point
    if np.linalg.norm(np.array(new_points[-1]) - np.array(points[-1])) > 0.00001:
        new_points.append(points[-1])
        
    return new_points



@app.post("/api/detect")
def run_detection(request: DetectionRequest):
    print(f"\n{'='*60}")
    print(f" NEW REQUEST: {request.dataset_name}")
    print(f"{'='*60}")

    # --- 0. CLEANUP PREVIOUS DEBUG FILES ---
    debug_dir = os.path.join(request.ortho_path, "debug_previews")
    training_dir = r"C:\code\rfdetr\datasets\003_oilpipe_ortho_tagged\patches"
    if os.path.exists(debug_dir):
        print(f"[CLEANUP] Deleting old debug files in {debug_dir}...")
        try:
            shutil.rmtree(debug_dir)
            time.sleep(0.1) 
        except Exception as e:
            print(f"[WARNING] Could not fully clear debug folder: {e}")
    os.makedirs(debug_dir, exist_ok=True)

    # 1. KML Parsing
    print(f"[KML] Reading trace from: {request.kml_path}")
    try:
        tree = ET.parse(request.kml_path)
        root, ns = tree.getroot(), {'kml': 'http://www.opengis.net/kml/2.2'}
        base_points = []
        for placemark in root.findall('.//kml:Placemark', ns):
            ls = placemark.find('.//kml:LineString', ns)
            if ls is not None:
                coords = ls.find('kml:coordinates', ns).text.strip().split()
                for c in coords:
                    lon, lat, *_ = map(float, c.split(','))
                    base_points.append((lon, lat))
                break 
        print(f"[KML] Original Vertices: {len(base_points)}")
        
        # Resample the trace
        base_points = resample_trace(base_points, step_meters=STEP_METERS)
        print(f"[KML] Resampled to {len(base_points)} points (~{STEP_METERS}m intervals).")
        
    except Exception as e:
        print(f"[ERROR] KML Parse failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    # 2. VRT Assembly
    if os.path.isfile(request.ortho_path):
        vrt_path = request.ortho_path
        print(f"[VRT] Using single TIFF: {vrt_path}")
    else:
        tifs = glob.glob(os.path.join(request.ortho_path, "*.tif"))
        vrt_path = os.path.join(request.ortho_path, "mosaic_reference.vrt")
        print(f"[VRT] Creating Virtual Raster from {len(tifs)} tiles...")
        vrt = gdal.BuildVRT(vrt_path, tifs)
        vrt = None
        print(f"[VRT] Saved to: {vrt_path}")

    features = []
    state_totals = {s["name"]: 0.0 for s in PROCESS_STATES}
    total_project_length = 0.0

    box_annotator = sv.BoxAnnotator()
    label_annotator = sv.LabelAnnotator()

    # --- CONFIGURATION FOR AI ---
    # Define what size image the AI was trained to look at
    AI_INPUT_SIZE = (1024, 1024) 

    # 3. Scanning Loop
    with rasterio.open(vrt_path) as src:
        bounds = src.bounds
        print(f"[SCAN] Raster Bounds: {bounds}")
        
        for i in range(len(base_points) - 1):
            p1, p2 = base_points[i], base_points[i+1]
            mid_lon, mid_lat = (p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2
            
            dist = math.sqrt((p2[0]-p1[0])**2 + (p2[1]-p1[1])**2)
            segment_meters = dist * 111320 
            total_project_length += segment_meters
            
            # Check if within image bounds
            if not (bounds.left <= mid_lon <= bounds.right and bounds.bottom <= mid_lat <= bounds.top):
                print(f"  > Segment {i:03}: OUTSIDE raster bounds. Skipping AI.")
            else:
                px, py = src.index(mid_lon, mid_lat)
                
                # --- DYNAMIC & GAPLESS WINDOW CALCULATION ---
                res_x = src.res[0]
                actual_gsd_meters = res_x * 111320 if res_x < 0.0001 else res_x
                
                # Window covers exactly the STEP_METERS + 10% overlap
                window_meters = STEP_METERS * 1.1 
                required_px = int(window_meters / actual_gsd_meters)
                
                # RAM Safety Gate: Prevent crashes if GSD math gets weird. 
                # Caps memory usage to reasonable limits (max ~8000px box)
                required_px = min(max(required_px, 320), 8000)

                window = Window(py - required_px//2, px - required_px//2, required_px, required_px)
                
                try:
                    # boundless=True prevents crashing on the edge of the map
                    patch = src.read(window=window, boundless=True, fill_value=0)
                    
                    if patch.dtype != np.uint8:
                        patch = np.clip(patch, 0, 255).astype(np.uint8)
                    
                    patch_rgb = np.moveaxis(patch, 0, -1)
                    if patch_rgb.shape[-1] == 4: 
                        patch_rgb = patch_rgb[:, :, :3]

                    # Scale to match AI training dimensions
                    patch_resized = cv2.resize(patch_rgb, AI_INPUT_SIZE, interpolation=cv2.INTER_LANCZOS4)

                    # RGB to BGR for OpenCV
                    patch_bgr = cv2.cvtColor(patch_resized, cv2.COLOR_RGB2BGR)
                    
                    annotated_img = patch_bgr.copy()
                    
                    
                    
                    
                    if request.run_inference:
                        detector = get_model()
                        temp_filename = os.path.join(debug_dir, f"ai_input_temp_{uuid.uuid4().hex}.jpg")
                        cv2.imwrite(temp_filename, patch_bgr)
                        
                        detections = detector.predict(temp_filename, conf=0.3)
                        detected_states_for_this_segment = []
                        if len(detections) > 0:
                            detected_names = [CUSTOM_CLASSES[cid] for cid in detections.class_id]
                            for state in PROCESS_STATES:
                                if state["class"] in detected_names:
                                    detected_states_for_this_segment.append(state)

                            # DRAW AI BOXES
                            labels = [f"{CUSTOM_CLASSES[cid]} {conf:.2f}" 
                                      for cid, conf in zip(detections.class_id, detections.confidence)]
                            
                            annotated_img = box_annotator.annotate(scene=annotated_img, detections=detections)
                            annotated_img = label_annotator.annotate(scene=annotated_img, detections=detections, labels=labels)
                            
                            print(f"  > Segment {i:03}: AI DETECTED {detected_names}")
                        else:
                            print(f"  > Segment {i:03}: AI scanned - No objects found.")
                        
                        if os.path.exists(temp_filename): os.remove(temp_filename)

                    # Add Metadata Overlay
                    state_names = ", ".join([s["name"] for s in detected_states_for_this_segment]) if detected_states_for_this_segment else "None"
                    cv2.putText(annotated_img, f"SEG: {i:03} | {window_meters:.1f}m | STATE: {state_names}", (10, 30), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    
                    # Draw a small center crosshair
                    h, w, _ = annotated_img.shape
                    cv2.drawMarker(annotated_img, (w//2, h//2), (0, 255, 0), cv2.MARKER_CROSS, 20, 2)

                    # Save preview
                    seg_filename = f"segment_{i:03}.jpg"
                    cv2.imwrite(os.path.join(debug_dir, seg_filename), annotated_img)
                    # cv2.imwrite(os.path.join(training_dir, seg_filename), patch_bgr)

                except Exception as e:
                    print(f"  > Segment {i:03}: ERROR reading window: {e}")

            # Update features for the Frontend
            for state in detected_states_for_this_segment:
                features.append({
                    "type": "Feature",
                    "properties": {"state": state["name"], "color": state["color"], "type": "progress_ribbon"},
                    # Set offset to 0 so the line sits perfectly in the center of the trace
                    "geometry": {"type": "LineString", "coordinates": offset_segment(p1, p2, state["offset"])} 
                })
                state_totals[state["name"]] += segment_meters

    print(f"\n[DONE] Scan finished. Total: {total_project_length:.1f}m")
    for s, m in state_totals.items():
        print(f"  - {s}: {m:.1f}m ({round((m/total_project_length)*100, 1) if total_project_length > 0 else 0}%)")

    return {
        "dataset": request.dataset_name,
        "success": True,
        "summary": {
            "total_meters": round(total_project_length, 2),
            "states": [{"name": n, "meters": round(m, 2), "percent": round((m/total_project_length)*100, 1) if total_project_length > 0 else 0} for n, m in state_totals.items()]
        },
        "trace": {"type": "FeatureCollection", "features": features}
    }
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)