# Drone Photogrammetry Server & Web Viewer

THIS WAS WRITTEN WITH AN LLLM, DONT TRUST IT

A full-stack application that automates the processing of drone imagery into 3D orthomosaics using Agisoft Metashape, and serves them to a React/Leaflet web map.

## 📋 Prerequisites

Before you begin, ensure you have the following installed:
* **Node.js** (v18+ recommended)
* **Anaconda** or **Miniconda**
* **Agisoft Metashape Professional** (v2.1+) with a valid license.

---

## 🛠️ 1. Initial Setup

### Backend (Python / Metashape)
We use Conda to manage the Python environment and ensure Metashape's dependencies run cleanly.

1. Open your terminal (Anaconda Prompt recommended) and create the environment:
   conda create -n photogrammetry python=3.10

2. Activate the environment:
   conda activate photogrammetry

3. Install the required Python packages:
   pip install fastapi uvicorn python-multipart python-dotenv

### Frontend (React / Vite)
We use `pnpm` for fast and efficient Node package management.

1. **Validate/Install `pnpm`**: Check if you have it installed by running:
   pnpm -v
   *(If the command is not found, install it globally using npm: `npm install -g pnpm`)*

2. **Install Frontend Dependencies**:
   Navigate to the project root (or your frontend folder) and install the packages:
   pnpm install

---

## 🚀 2. Running the Application

You will need two terminal windows open—one for the backend server and one for the frontend UI.

### Start the Python Backend
In your first terminal, ensure your Conda environment is active, then start the server:
   conda activate photogrammetry
   python server.py

The backend API will typically run on `http://localhost:8000`.

### Start the Frontend UI
In your second terminal, run the Vite development server:
   pnpm run dev

The frontend will be available at `http://localhost:5173`. Open this link in your browser to interact with the map and upload datasets.

---

## 🧹 3. Utility Commands

If you need to completely reset your workspace (useful for debugging or starting a fresh processing batch), you can use the built-in clean command.

This will **permanently delete** the `_outputs/` folder and the local database file.

   pnpm run clean

---

## ⚙️ Configuration Notes

**Metashape Executable Path**
By default, the backend looks for Metashape at `C:\Program Files\Agisoft\Metashape Pro\metashape.exe`. 
If your installation is in a different location, you can define it by creating a `.env` file in the root directory:

METASHAPE_BIN_PATH="D:\Your\Custom\Path\metashape.exe"

---

## Detection server

Located in the examples folder, the detection_server script iterates over TIFF files along a designated KML path to execute the detection model and calculate overall work progress.