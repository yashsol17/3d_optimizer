"""
Client for the 3D Asset Optimization Engine.

Standard library only — no pip install — so it also runs inside the Python
interpreters that ship with DCC tools and game engines.

    from mesh_optimizer import optimize_file
    report = optimize_file("chair.glb", out_path="chair_lod1.glb", ratio=0.35)
    print(report["polygon_reduction_percent"])

Command line:

    python mesh_optimizer.py chair.glb -o chair_lod1.glb --ratio 0.35
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import os
import sys
import urllib.error
import urllib.request
import uuid

DEFAULT_URL = os.environ.get("MESH_OPTIMIZER_URL", "http://127.0.0.1:8000")
DEFAULT_RATIO = 0.35


class OptimizerError(RuntimeError):
    """The service rejected the request or failed to process the mesh."""


def _encode_multipart(fields: dict, file_field: str, file_path: str) -> tuple[bytes, str]:
    """Build a multipart/form-data body without pulling in `requests`."""
    boundary = f"----meshopt{uuid.uuid4().hex}"
    crlf = b"\r\n"
    body = bytearray()

    for name, value in fields.items():
        body += b"--" + boundary.encode() + crlf
        body += f'Content-Disposition: form-data; name="{name}"'.encode() + crlf + crlf
        body += str(value).encode() + crlf

    filename = os.path.basename(file_path)
    ctype = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    body += b"--" + boundary.encode() + crlf
    body += f'Content-Disposition: form-data; name="{file_field}"; filename="{filename}"'.encode() + crlf
    body += f"Content-Type: {ctype}".encode() + crlf + crlf
    with open(file_path, "rb") as fh:
        body += fh.read()
    body += crlf + b"--" + boundary.encode() + b"--" + crlf

    return bytes(body), f"multipart/form-data; boundary={boundary}"


def health(url: str = DEFAULT_URL, timeout: int = 30) -> dict:
    """Ask the service whether it is up and Blender is usable."""
    with urllib.request.urlopen(f"{url.rstrip('/')}/api/v1/health", timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def optimize_file(
    input_path: str,
    out_path: str | None = None,
    ratio: float = DEFAULT_RATIO,
    url: str = DEFAULT_URL,
    api_key: str | None = None,
    timeout: int = 600,
) -> dict:
    """
    Optimize one mesh and write the result to `out_path`.

    Returns the metrics reported by the service. Raises OptimizerError on failure.
    """
    if not os.path.isfile(input_path):
        raise OptimizerError(f"No such file: {input_path}")

    if out_path is None:
        stem, ext = os.path.splitext(input_path)
        out_path = f"{stem}_optimized{ext or '.glb'}"

    body, content_type = _encode_multipart({"ratio": ratio}, "file", input_path)
    endpoint = f"{url.rstrip('/')}/api/v1/optimize?format=binary"

    request = urllib.request.Request(endpoint, data=body, method="POST")
    request.add_header("Content-Type", content_type)
    request.add_header("Content-Length", str(len(body)))
    if api_key:
        request.add_header("X-API-Key", api_key)

    try:
        with urllib.request.urlopen(request, timeout=timeout) as resp:
            payload = resp.read()
            headers = resp.headers
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")
        try:
            detail = json.loads(detail).get("detail", detail)
        except ValueError:
            pass
        raise OptimizerError(f"HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise OptimizerError(f"Could not reach {url}: {exc.reason}") from exc

    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
    with open(out_path, "wb") as fh:
        fh.write(payload)

    def num(header: str, cast=float):
        value = headers.get(header)
        try:
            return cast(value)
        except (TypeError, ValueError):
            return None

    return {
        "job_id": headers.get("X-Mesh-Job-Id"),
        "output_path": os.path.abspath(out_path),
        "output_bytes": len(payload),
        "ratio": num("X-Mesh-Ratio"),
        "polygon_reduction_percent": num("X-Mesh-Reduction-Percent"),
        "original_faces": num("X-Mesh-Original-Faces", int),
        "optimized_faces": num("X-Mesh-Optimized-Faces", int),
        "processing_seconds": num("X-Mesh-Processing-Seconds"),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Optimize a 3D mesh via the optimization service.")
    parser.add_argument("input", help="Mesh file to optimize (.glb, .gltf, .fbx, .obj)")
    parser.add_argument("-o", "--output", help="Where to write the optimized mesh")
    parser.add_argument("-r", "--ratio", type=float, default=DEFAULT_RATIO,
                        help="Target density 0.01-1.0 (default: %(default)s)")
    parser.add_argument("--url", default=DEFAULT_URL, help="Service URL (default: %(default)s)")
    parser.add_argument("--api-key", default=os.environ.get("MESH_OPTIMIZER_KEY"),
                        help="Sent as X-API-Key when the service requires it")
    parser.add_argument("--json", action="store_true", help="Print the report as JSON")
    args = parser.parse_args(argv)

    try:
        report = optimize_file(args.input, args.output, args.ratio, args.url, args.api_key)
    except OptimizerError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"{report['original_faces']:,} -> {report['optimized_faces']:,} faces "
              f"({report['polygon_reduction_percent']}% removed) in {report['processing_seconds']}s")
        print(f"wrote {report['output_path']} ({report['output_bytes'] / 1024:.1f} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
