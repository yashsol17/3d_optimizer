# Integration clients

The service exposes a versioned HTTP API so engines and build pipelines can use
the optimizer directly, without the web UI. Interactive docs are served at
`/docs` and the machine-readable schema at `/openapi.json` while the server runs.

## API

| Route | Purpose |
|---|---|
| `GET /api/v1/health` | Service status, Blender version, limits, supported formats |
| `POST /api/v1/optimize` | Submit one mesh, get the decimated result |

`POST /api/v1/optimize` takes a multipart form with `file` (the mesh) and
`ratio` (0.01–1.0, default 0.35), plus a `format` query parameter:

- `format=json` (default) — metrics plus a `download_url`
- `format=binary` — the optimized `.glb` itself, with metrics in `X-Mesh-*` headers

Errors come back as `{"detail": "..."}` with `400` (bad format, bad ratio,
unreadable mesh), `413` (too large), `504` (Blender timed out) or `500`.

Set the `API_KEY` environment variable on the server to require an `X-API-Key`
header; leave it unset and the API is open.

### curl

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/optimize?format=binary" \
  -F "file=@chair.glb" -F "ratio=0.35" -o chair_lod1.glb
```

## Python (`python/mesh_optimizer.py`)

Standard library only, so it runs in engine and DCC Python interpreters without
`pip install`.

```python
from mesh_optimizer import optimize_file

report = optimize_file("chair.glb", out_path="chair_lod1.glb", ratio=0.35,
                       url="http://127.0.0.1:8000")
print(report["polygon_reduction_percent"], "% of faces removed")
```

As a command line tool:

```bash
python clients/python/mesh_optimizer.py chair.glb -o chair_lod1.glb --ratio 0.35
```

`MESH_OPTIMIZER_URL` and `MESH_OPTIMIZER_KEY` are read from the environment when
`--url` / `--api-key` are omitted.

## Unreal Engine (`unreal/optimize_selected.py`)

Select Static Meshes in the Content Browser, then run the script from
**Tools → Execute Python Script**. Each mesh is exported to glTF, optimized by
the service, and imported back into `/Game/Optimized` as a new asset — originals
are never modified.

Needs the **Python Editor Script Plugin** and the **glTF Exporter** plugin enabled.

> This script has not been run against a live editor; it was written without an
> Unreal install available. Test it on a scratch project first.

## Other engines

Any tool that can POST a file can use the API. Unity's `UnityWebRequest`, a
Node build step, or a shell script in CI all work the same way: send the mesh,
write back the bytes. Keep to `/api/v1` routes — the web UI's `/optimize`
endpoint is for the browser and may change.
