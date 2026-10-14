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
# STORAGE_DIR can be redirected with an env var: container filesystems are often
# read-only outside /tmp, and the uploads are disposable either way.
STORAGE_DIR = os.environ.get("STORAGE_DIR", os.path.join(BACKEND_DIR, "storage"))
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

# --- Server ---
HOST = os.environ.get("HOST", "127.0.0.1")   # containers set 0.0.0.0
PORT = int(os.environ.get("PORT", "8000"))   # Hugging Face Spaces uses 7860

# --- Limits (the deployed app is public) ---
MAX_UPLOAD_MB = int(os.environ.get("MAX_UPLOAD_MB", "80"))
KEEP_FILES = int(os.environ.get("KEEP_FILES", "40"))  # per storage folder
