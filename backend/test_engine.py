import sys
import subprocess
import json
import os
from pathlib import Path

# 1. Setup system path using pathlib so Python finds your modules
project_root = Path(__file__).resolve().parent
sys.path.append(str(project_root))

# Import the standalone function, not the class
from core.worker import run_job

def test_real_flow():
    print("=== STARTING REAL ARCHITECTURE FLOW TEST ===\n")
    
    # 2. Setup mock paths
    dataset_name = "test_drone_flight"
    output_dir = project_root / "_outputs" / dataset_name
    output_dir_str = str(output_dir.resolve())
    image_dir_str = str((project_root / "_datasets" / dataset_name).resolve())
    
    # 3. Define the config exactly as FastAPI will pass it
    config = {
        "engine": "metashape",
        "profile": "mapping",
        "template": "FULL_PROCESS"
    }
    
    print(f"\n--- Triggering run_job (Profile: {config['profile']} | Template: {config['template']}) ---")
    
    # 4. Call the function! It handles the Factory, Engine, and Worker internally.
    try:
        run_job(
            dataset_name=dataset_name, 
            image_dir=image_dir_str, 
            output_dir=output_dir_str, 
            job_id="TEST_JOB_001", 
            config=config
        )
        print("\n=== FLOW TEST FINISHED ===")
        print("If you saw the tasks execute in the terminal, the routing works perfectly!")
    except Exception as e:
        print("\n=== FLOW TEST FAILED ===")
        print(f"Error: {e}")

def test_modular_flow():
    print("=== STARTING MODULAR SUBPROCESS FLOW TEST ===\n")
    dataset_name = "FM-PP-7"

    
    # 2. Setup paths
    true_root = project_root.parent
    output_dir = true_root / "_outputs" / f"{dataset_name}_out"
    # Ensure folder exists so Metashape doesn't complain
    output_dir.mkdir(parents=True, exist_ok=True)
    
    image_dir = true_root / "_datasets" / dataset_name
    
    # 3. Define the config
    config = {
        "engine": "metashape",
        "profile": "tiled_model",
        "template": "FULL_PROCESS"
    }
    
    # 4. SUBPROCESS LOGIC (The "Hacky" but correct way)
    try:
        # Path to your Metashape Pro executable
        metashape_bin = r"C:\Program Files\Agisoft\Metashape Pro\metashape.exe"
        
        # Path to your worker entry point (the file containing run_job)
        worker_script = project_root / "core" / "worker.py"
        
        print(f"Launching Metashape Subprocess...")
        
        cmd = [
            metashape_bin,
            "-r", str(worker_script),      # The script to run
            dataset_name,                  # sys.argv[1]
            str(image_dir.resolve()),      # sys.argv[2]
            str(output_dir.resolve()),     # sys.argv[3]
            "TEST_JOB_999",                # sys.argv[4]
            json.dumps(config)             # sys.argv[5]
        ]
        
        # This blocks until the job is done
        result = subprocess.run(cmd, check=True)
        
        if result.returncode == 0:
            print("\n=== MODULAR TEST SUCCESSFUL ===")
        else:
            print(f"\n=== MODULAR TEST FAILED with code {result.returncode} ===")

    except Exception as e:
        print(f"\n=== ERROR LAUNCHING SUBPROCESS ===\n{e}")

if __name__ == "__main__":
    test_modular_flow()