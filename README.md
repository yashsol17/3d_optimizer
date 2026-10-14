---
title: Mesh Optimizer
emoji: 🪐
colorFrom: gray
colorTo: red
sdk: docker
app_port: 7860
pinned: false
short_description: Decimate 3D assets with headless Blender and compare them
---

# 3D Optimization Pipeline

Upload a 3D model (GLB/GLTF/FBX/OBJ), decimate it with Blender, and compare the original vs. optimized mesh in the browser.

## Project structure

```
3d-optimization-pipeline/
├── backend/                     # FastAPI server + processing
│   ├── main.py                  # API entry point (serves UI, /optimize, /storage)
│   ├── config.py                # All paths + Blender location
│   ├── requirements.txt         # Python dependencies
│   ├── core/                    # Mesh analysis & ML logic
│   │   ├── feature_extractor.py #   geometry features via trimesh
│   │   ├── ai_engine.py         #   (planned) decimation-ratio predictor
│   │   └── evaluator.py         #   (planned) quality scoring
│   ├── blender_scripts/         # Scripts run inside Blender (bpy)
│   │   ├── process_mesh.py      #   cleanup + decimate + export GLB
│   │   └── generate_dataset.py  #   (planned) build training dataset
│   ├── data/                    # ML training data
│   │   ├── dataset.csv
│   │   └── raw_models/
│   └── storage/                 # Runtime files (served at /storage)
│       ├── inputs/              #   uploaded models
│       └── outputs/             #   optimized models
└── frontend/
    └── index.html               # Web UI (model-viewer comparison)
```

## Run

```bash
pip install -r backend/requirements.txt
python backend/main.py
----------------------------------------
.venv\Scripts\python.exe backend\main.py
----------------------------------------
```

Open http://127.0.0.1:8000. If Blender isn't at the default path, set the `BLENDER_PATH` environment variable.

## Deploy

The app ships as a Docker image that bundles headless Blender 4.5 LTS, so the host
needs nothing but Docker. It is configured for Hugging Face Spaces (Docker SDK),
which serves on port 7860.

Run the image anywhere:

```bash
docker build -t mesh-optimizer .
docker run --rm -p 7860:7860 mesh-optimizer
```

Deploy to a Hugging Face Space:

```bash
git remote add space https://huggingface.co/spaces/<user>/<space-name>
git push space main
```

The Space builds the Dockerfile and publishes at `https://<user>-<space-name>.hf.space`.

### Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `BLENDER_PATH` | Windows install path | Blender executable |
| `STORAGE_DIR` | `backend/storage` | Where uploads and outputs are written |
| `HOST` / `PORT` | `127.0.0.1` / `8000` | Bind address (container sets `0.0.0.0` / `7860`) |
| `MAX_UPLOAD_MB` | `80` | Rejects larger uploads |
| `KEEP_FILES` | `40` | Files kept per storage folder before pruning |
