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
```

Open http://127.0.0.1:8000. If Blender isn't at the default path, set the `BLENDER_PATH` environment variable.
