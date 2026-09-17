"""
Central configuration: filesystem paths and external tool locations.
All paths are resolved relative to this file, so the server works from any working directory.
"""
import os

# --- Project layout ---
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)
FRONTEND_DIR = os.path.join(PROJECT_ROOT, "frontend")

# --- Storage (uploaded + optimized models) ---
STORAGE_DIR = os.path.join(BACKEND_DIR, "storage")
INPUTS_DIR = os.path.join(STORAGE_DIR, "inputs")
OUTPUTS_DIR = os.path.join(STORAGE_DIR, "outputs")

# --- ML data ---
DATA_DIR = os.path.join(BACKEND_DIR, "data")
DATASET_CSV = os.path.join(DATA_DIR, "dataset.csv")
RAW_MODELS_DIR = os.path.join(DATA_DIR, "raw_models")

# --- Blender ---
# Override with the BLENDER_PATH environment variable if Blender lives elsewhere.
BLENDER_PATH = os.environ.get(
    "BLENDER_PATH", r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
)
BLENDER_SCRIPTS_DIR = os.path.join(BACKEND_DIR, "blender_scripts")
PROCESS_MESH_SCRIPT = os.path.join(BLENDER_SCRIPTS_DIR, "process_mesh.py")
