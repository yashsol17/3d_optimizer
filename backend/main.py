from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os
import re
from api import router as api_router
from core import pipeline
from config import (
    STORAGE_DIR, INPUTS_DIR, OUTPUTS_DIR,
    FRONTEND_DIR, HOST, PORT,
    MAX_UPLOAD_MB, KEEP_FILES, API_VERSION,
)

app = FastAPI(
    title="3D Asset Optimization Engine",
    version=API_VERSION,
    description=(
        "Mesh decimation as a service. The browser UI lives at `/`; engines and "
        "build pipelines should use the versioned routes under `/api/v1`."
    ),
)

# Engines and tools call this cross-origin; the API is read-only on their data.
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
    expose_headers=[
        "X-Mesh-Job-Id", "X-Mesh-Ratio", "X-Mesh-Reduction-Percent",
        "X-Mesh-Original-Faces", "X-Mesh-Optimized-Faces", "X-Mesh-Processing-Seconds",
    ],
)

app.include_router(api_router)

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

    # Same pipeline the API uses, so the UI and integrations never diverge
    try:
        report = pipeline.optimize(input_path, output_path, ratio)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except pipeline.MeshParseError as exc:
        raise HTTPException(status_code=400, detail=f"Failed to parse input 3D mesh: {exc}")
    except pipeline.BlenderTimeout as exc:
        raise HTTPException(status_code=504, detail=str(exc))
    except pipeline.BlenderError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    features = report["original_features"]
    optimized_features = report["optimized_features"]

    prune(INPUTS_DIR)
    prune(OUTPUTS_DIR)

    return {
        "status": "success",
        "original_url": f"/storage/inputs/{filename}",
        "optimized_url": f"/storage/outputs/{output_filename}",
        "original_features": features,
        "optimized_features": optimized_features,
        "polygon_reduction_percent": report["polygon_reduction_percent"],
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=HOST, port=PORT)