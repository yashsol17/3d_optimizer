"""
Central configuration: filesystem paths and external tool locations.
All paths are resolved relative to this file, so the server works from any working directory.
"""
import glob
import os
import sys

# --- Project layout ---
# Inside a PyInstaller bundle the code lives in a temporary extraction folder
# (sys._MEIPASS); everywhere else it is the repository itself.
BUNDLE_DIR = getattr(sys, "_MEIPASS", None)
BACKEND_DIR = os.path.join(BUNDLE_DIR, "backend") if BUNDLE_DIR else os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = BUNDLE_DIR if BUNDLE_DIR else os.path.dirname(BACKEND_DIR)
FRONTEND_DIR = os.path.join(PROJECT_ROOT, "frontend")
IS_FROZEN = bool(BUNDLE_DIR)

# --- Storage (uploaded + optimized models) ---
# STORAGE_DIR can be redirected with an env var: container filesystems are often
# read-only outside /tmp, and the uploads are disposable either way.
def _default_storage() -> str:
    """
    Where uploads and results live.

    A frozen desktop build may sit in Program Files (read-only) and its code
    folder is a temp dir wiped on exit, so user data goes to the per-user app
    data directory instead.
    """
    if IS_FROZEN:
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
        return os.path.join(base, "MeshOptimizer", "storage")
    return os.path.join(BACKEND_DIR, "storage")


STORAGE_DIR = os.environ.get("STORAGE_DIR", _default_storage())
INPUTS_DIR = os.path.join(STORAGE_DIR, "inputs")
OUTPUTS_DIR = os.path.join(STORAGE_DIR, "outputs")

# --- ML data ---
DATA_DIR = os.path.join(BACKEND_DIR, "data")
DATASET_CSV = os.path.join(DATA_DIR, "dataset.csv")
RAW_MODELS_DIR = os.path.join(DATA_DIR, "raw_models")

# --- Blender ---
def detect_blender() -> str:
    """
    Find a Blender executable.

    BLENDER_PATH wins when set. Otherwise look through the usual install
    locations for each OS, newest version first, then fall back to whatever is
    on PATH. The desktop build depends on this: an installed copy of Blender
    is never at a path we can hardcode.
    """
    from shutil import which

    env_path = os.environ.get("BLENDER_PATH")
    if env_path:
        return env_path

    patterns = [
        r"C:\Program Files\Blender Foundation\Blender*\blender.exe",
        r"C:\Program Files (x86)\Blender Foundation\Blender*\blender.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Blender Foundation\Blender*\blender.exe"),
        r"C:\Program Files\Steam\steamapps\common\Blender\blender.exe",
        "/Applications/Blender.app/Contents/MacOS/Blender",
        "/Applications/Blender*/Blender.app/Contents/MacOS/Blender",
        "/usr/share/blender/blender",
        "/opt/blender/blender",
    ]

    found = []
    for pattern in patterns:
        found.extend(glob.glob(pattern))
    if found:
        # Highest version number last alphabetically → prefer the newest install
        return sorted(found)[-1]

    return which("blender") or which("blender.exe") or "blender"


BLENDER_PATH = detect_blender()
BLENDER_SCRIPTS_DIR = os.path.join(BACKEND_DIR, "blender_scripts")
PROCESS_MESH_SCRIPT = os.path.join(BLENDER_SCRIPTS_DIR, "process_mesh.py")

# --- Server ---
HOST = os.environ.get("HOST", "127.0.0.1")   # containers set 0.0.0.0
PORT = int(os.environ.get("PORT", "8000"))   # Hugging Face Spaces uses 7860

# --- Limits (the deployed app is public) ---
MAX_UPLOAD_MB = int(os.environ.get("MAX_UPLOAD_MB", "80"))
KEEP_FILES = int(os.environ.get("KEEP_FILES", "40"))  # per storage folder
BLENDER_TIMEOUT = int(os.environ.get("BLENDER_TIMEOUT", "300"))  # seconds

# --- API ---
# Set API_KEY to require an X-API-Key header on /api/v1 routes. Empty = open.
API_KEY = os.environ.get("API_KEY", "")
API_VERSION = "1.0"
MIN_RATIO_DEFAULT = 0.35  # used when a caller omits the ratio
