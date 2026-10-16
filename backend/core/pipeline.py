"""
The optimization pipeline, shared by the web UI and the public API:
analyse the mesh, decimate it in headless Blender, analyse the result.

Transport concerns (HTTP status codes, uploads) stay out of here on purpose —
callers translate these exceptions into whatever their protocol needs.
"""
import os
import subprocess
import time

from config import BLENDER_PATH, PROCESS_MESH_SCRIPT, BLENDER_TIMEOUT
from core.feature_extractor import extract_mesh_features

MIN_RATIO = 0.01
MAX_RATIO = 1.0


class PipelineError(Exception):
    """Base class for optimization failures."""


class MeshParseError(PipelineError):
    """The input file could not be read as a 3D mesh."""


class BlenderError(PipelineError):
    """Blender ran but produced no output."""


class BlenderTimeout(PipelineError):
    """Blender exceeded the time budget."""


def validate_ratio(ratio: float) -> float:
    """Clamp-check the decimation ratio; out-of-range values corrupt the output."""
    try:
        ratio = float(ratio)
    except (TypeError, ValueError):
        raise ValueError("ratio must be a number")
    if not (MIN_RATIO <= ratio <= MAX_RATIO):
        raise ValueError(f"ratio must be between {MIN_RATIO} and {MAX_RATIO}")
    return ratio


def optimize(input_path: str, output_path: str, ratio: float = 0.35) -> dict:
    """
    Decimate `input_path` into `output_path` and return the before/after report.

    Raises MeshParseError, BlenderTimeout or BlenderError on failure.
    """
    ratio = validate_ratio(ratio)
    started = time.time()

    try:
        original = extract_mesh_features(input_path)
    except Exception as exc:
        raise MeshParseError(str(exc)) from exc

    cmd = [
        BLENDER_PATH,
        "--background",
        "--python", PROCESS_MESH_SCRIPT,
        "--",
        "--input", input_path,
        "--output", output_path,
        "--ratio", str(ratio),
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=BLENDER_TIMEOUT)
    except subprocess.TimeoutExpired:
        raise BlenderTimeout(
            f"Blender exceeded {BLENDER_TIMEOUT}s on this model."
        )
    except FileNotFoundError:
        raise BlenderError(
            f"Blender executable not found at {BLENDER_PATH}. Set the BLENDER_PATH environment variable."
        )

    if not os.path.exists(output_path):
        tail = " ".join((result.stderr or "").strip().splitlines()[-4:])
        raise BlenderError(f"Blender produced no output file. {tail}")

    optimized = extract_mesh_features(output_path)

    reduction = 0.0
    if original["face_count"]:
        reduction = round((1 - optimized["face_count"] / original["face_count"]) * 100, 2)

    return {
        "ratio": ratio,
        "original_features": original,
        "optimized_features": optimized,
        "polygon_reduction_percent": reduction,
        "processing_seconds": round(time.time() - started, 2),
        "output_bytes": os.path.getsize(output_path),
    }
