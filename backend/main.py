from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import subprocess
import shutil
import os
import re
import json
from core.feature_extractor import extract_mesh_features
from config import (
    BLENDER_PATH, STORAGE_DIR, INPUTS_DIR, OUTPUTS_DIR,
    FRONTEND_DIR, PROCESS_MESH_SCRIPT, HOST, PORT,
    MAX_UPLOAD_MB, KEEP_FILES,
)

app = FastAPI(title="3D Model Optimization Engine API")

os.makedirs(INPUTS_DIR, exist_ok=True)
os.makedirs(OUTPUTS_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {".glb", ".gltf", ".fbx", ".obj"}


def safe_name(filename: str) -> str:
    """Strip any path components and odd characters from an uploaded filename."""
    base = os.path.basename(filename or "").replace("\\", "/").split("/")[-1]
    base = re.sub(r"[^A-Za-z0-9._-]", "_", base).lstrip(".")
    return base[:120] or "model.glb"


def prune(directory: str, keep: int = KEEP_FILES) -> None:
    """Keep only the newest files: the deployed disk is small and disposable."""
    try:
        files = [os.path.join(directory, f) for f in os.listdir(directory)]
        files = [f for f in files if os.path.isfile(f) and not f.endswith(".gitkeep")]
        for old in sorted(files, key=os.path.getmtime, reverse=True)[keep:]:
            os.remove(old)
    except OSError:
        pass  # pruning is housekeeping, never fatal

# Mount storage directory so the frontend can access .glb files directly
app.mount("/storage", StaticFiles(directory=STORAGE_DIR), name="storage")

@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    html_file = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(html_file):
        with open(html_file, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>index.html not found. Please create frontend/index.html</h1>"

@app.post("/optimize")
async def optimize_model(
    file: UploadFile = File(...),
    ratio: float = Form(0.35)
):
    filename = safe_name(file.filename)
    if os.path.splitext(filename)[1].lower() not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Use one of: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    input_path = os.path.join(INPUTS_DIR, filename)
    output_filename = f"optimized_{filename}"
    output_path = os.path.join(OUTPUTS_DIR, output_filename)

    # Save the upload, refusing anything oversized before it fills the disk
    limit = MAX_UPLOAD_MB * 1024 * 1024
    written = 0
    with open(input_path, "wb") as buffer:
        while chunk := await file.read(1024 * 1024):
            written += len(chunk)
            if written > limit:
                buffer.close()
                os.remove(input_path)
                raise HTTPException(
                    status_code=413,
                    detail=f"File is larger than the {MAX_UPLOAD_MB} MB limit.",
                )
            buffer.write(chunk)

    # Step 1: Extract Original Features
    try:
        features = extract_mesh_features(input_path)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse input 3D mesh: {str(e)}")

    # Step 2: Invoke Blender Process
    cmd = [
        BLENDER_PATH,
        "--background",
        "--python", PROCESS_MESH_SCRIPT,
        "--",
        "--input", input_path,
        "--output", output_path,
        "--ratio", str(ratio)
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    except subprocess.TimeoutExpired:
        raise HTTPException(
            status_code=504,
            detail="Blender took too long on this model. Try a smaller asset.",
        )

    if not os.path.exists(output_path):
        tail = (result.stderr or "").strip().splitlines()[-4:]
        raise HTTPException(
            status_code=500,
            detail="Blender failed to produce an output file. " + " ".join(tail)
        )

    # Step 3: Extract Optimized Features
    optimized_features = extract_mesh_features(output_path)

    prune(INPUTS_DIR)
    prune(OUTPUTS_DIR)

    return {
        "status": "success",
        "original_url": f"/storage/inputs/{filename}",
        "optimized_url": f"/storage/outputs/{output_filename}",
        "original_features": features,
        "optimized_features": optimized_features,
        "polygon_reduction_percent": round((1 - (optimized_features['face_count'] / features['face_count'])) * 100, 2)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=HOST, port=PORT)