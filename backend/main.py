from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import subprocess
import shutil
import os
import json
from core.feature_extractor import extract_mesh_features
from config import (
    BLENDER_PATH, STORAGE_DIR, INPUTS_DIR, OUTPUTS_DIR,
    FRONTEND_DIR, PROCESS_MESH_SCRIPT,
)

app = FastAPI(title="3D Model Optimization Engine API")

os.makedirs(INPUTS_DIR, exist_ok=True)
os.makedirs(OUTPUTS_DIR, exist_ok=True)

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
    input_path = os.path.join(INPUTS_DIR, file.filename)
    output_filename = f"optimized_{file.filename}"
    output_path = os.path.join(OUTPUTS_DIR, output_filename)

    # Save uploaded file
    with open(input_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

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

    result = subprocess.run(cmd, capture_output=True, text=True)

    if not os.path.exists(output_path):
        raise HTTPException(
            status_code=500, 
            detail=f"Blender failed to output file: {result.stderr}"
        )

    # Step 3: Extract Optimized Features
    optimized_features = extract_mesh_features(output_path)

    return {
        "status": "success",
        "original_url": f"/storage/inputs/{file.filename}",
        "optimized_url": f"/storage/outputs/{output_filename}",
        "original_features": features,
        "optimized_features": optimized_features,
        "polygon_reduction_percent": round((1 - (optimized_features['face_count'] / features['face_count'])) * 100, 2)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)