"""
Public API (v1) for engine and pipeline integration.

Stable contract — the web UI may change freely, but these routes and their
field names are what Unreal, Unity and build scripts depend on. Interactive
documentation is served at /docs, machine-readable schema at /openapi.json.
"""
import os
import shutil
import subprocess
import uuid

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from config import (
    API_KEY, API_VERSION, BLENDER_PATH, INPUTS_DIR, OUTPUTS_DIR,
    MAX_UPLOAD_MB, MIN_RATIO_DEFAULT,
)
from core import pipeline

router = APIRouter(prefix="/api/v1", tags=["optimization"])

SUPPORTED_FORMATS = [".glb", ".gltf", ".fbx", ".obj"]


# --------------------------------------------------------------- schemas
class MeshFeatures(BaseModel):
    vertex_count: int
    face_count: int
    surface_area: float
    volume: float
    is_watertight: bool
    bounding_box_x: float
    bounding_box_y: float
    bounding_box_z: float
    aspect_ratio: float


class OptimizeResponse(BaseModel):
    """Returned by POST /api/v1/optimize when format=json (the default)."""
    status: str = Field("success", examples=["success"])
    job_id: str = Field(..., description="Unique id for this run; also the output filename stem")
    ratio: float = Field(..., description="Target density actually applied")
    polygon_reduction_percent: float = Field(..., examples=[65.04])
    processing_seconds: float = Field(..., examples=[8.6])
    output_bytes: int
    download_url: str = Field(..., description="GET this to fetch the optimized mesh")
    original_features: MeshFeatures
    optimized_features: MeshFeatures


class HealthResponse(BaseModel):
    status: str
    api_version: str
    blender_available: bool
    blender_version: str | None
    supported_formats: list[str]
    max_upload_mb: int
    auth_required: bool


# ------------------------------------------------------------------ auth
def require_key(x_api_key: str | None = Header(default=None)):
    """No-op unless API_KEY is configured, so local use stays frictionless."""
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key header.")


# ---------------------------------------------------------------- routes
@router.get("/health", response_model=HealthResponse, summary="Service and Blender status")
def health() -> HealthResponse:
    """Check before submitting work: confirms Blender is present and usable."""
    version, available = None, False
    try:
        out = subprocess.run([BLENDER_PATH, "--version"], capture_output=True, text=True, timeout=30)
        if out.returncode == 0:
            version = (out.stdout or "").strip().splitlines()[0] if out.stdout else None
            available = True
    except (OSError, subprocess.SubprocessError):
        available = False

    return HealthResponse(
        status="ok" if available else "degraded",
        api_version=API_VERSION,
        blender_available=available,
        blender_version=version,
        supported_formats=SUPPORTED_FORMATS,
        max_upload_mb=MAX_UPLOAD_MB,
        auth_required=bool(API_KEY),
    )


@router.post(
    "/optimize",
    response_model=OptimizeResponse,
    dependencies=[Depends(require_key)],
    summary="Decimate a mesh and return the result",
    responses={
        200: {"description": "Optimized mesh (JSON report, or the binary file when format=binary)"},
        400: {"description": "Unsupported format, bad ratio, or unreadable mesh"},
        413: {"description": "Upload exceeds the size limit"},
        504: {"description": "Blender exceeded its time budget"},
    },
)
async def optimize(
    file: UploadFile = File(..., description="Mesh file: .glb, .gltf, .fbx or .obj"),
    ratio: float = Form(MIN_RATIO_DEFAULT, description="Target density, 0.01-1.0 (0.35 keeps 35% of faces)"),
    format: str = Query("json", pattern="^(json|binary)$",
                        description="json returns metrics plus a download URL; binary streams the mesh back"),
):
    """
    Submit one mesh, get the decimated version back.

    `format=binary` returns the file itself with the metrics in `X-Mesh-*`
    response headers, so an engine can write the bytes straight to disk
    without a second request.
    """
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in SUPPORTED_FORMATS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format '{ext or 'none'}'. Supported: {', '.join(SUPPORTED_FORMATS)}",
        )

    try:
        ratio = pipeline.validate_ratio(ratio)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    job_id = uuid.uuid4().hex[:12]
    input_path = os.path.join(INPUTS_DIR, f"{job_id}{ext}")
    output_name = f"{job_id}_optimized.glb"
    output_path = os.path.join(OUTPUTS_DIR, output_name)

    limit = MAX_UPLOAD_MB * 1024 * 1024
    written = 0
    with open(input_path, "wb") as buffer:
        while chunk := await file.read(1024 * 1024):
            written += len(chunk)
            if written > limit:
                buffer.close()
                os.remove(input_path)
                raise HTTPException(status_code=413, detail=f"File exceeds the {MAX_UPLOAD_MB} MB limit.")
            buffer.write(chunk)

    try:
        report = pipeline.optimize(input_path, output_path, ratio)
    except pipeline.MeshParseError as exc:
        raise HTTPException(status_code=400, detail=f"Could not read the mesh: {exc}")
    except pipeline.BlenderTimeout as exc:
        raise HTTPException(status_code=504, detail=str(exc))
    except pipeline.BlenderError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    if format == "binary":
        return FileResponse(
            output_path,
            media_type="model/gltf-binary",
            filename=output_name,
            headers={
                "X-Mesh-Job-Id": job_id,
                "X-Mesh-Ratio": str(report["ratio"]),
                "X-Mesh-Reduction-Percent": str(report["polygon_reduction_percent"]),
                "X-Mesh-Original-Faces": str(report["original_features"]["face_count"]),
                "X-Mesh-Optimized-Faces": str(report["optimized_features"]["face_count"]),
                "X-Mesh-Processing-Seconds": str(report["processing_seconds"]),
            },
        )

    return OptimizeResponse(
        job_id=job_id,
        download_url=f"/storage/outputs/{output_name}",
        **report,
    )
