"""
Build the standalone Windows executable.

    .venv\\Scripts\\python.exe desktop/build.py

Produces desktop/dist/MeshOptimizer.exe — a single file that needs no Python
on the target machine. Blender is NOT bundled (it is a ~1 GB application with
its own installer); the app detects an installed copy at startup and says so
clearly if none is found.
"""
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
NAME = "MeshOptimizer"
SEP = ";" if os.name == "nt" else ":"


def main() -> int:
    icon = os.path.join(HERE, "icon.ico")
    if not os.path.exists(icon):
        subprocess.run([sys.executable, os.path.join(HERE, "make_icon.py")], check=True)

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm", "--clean",
        "--onefile",
        "--windowed",                      # no console window
        "--name", NAME,
        "--icon", icon,
        "--distpath", os.path.join(HERE, "dist"),
        "--workpath", os.path.join(HERE, "build"),
        "--specpath", HERE,
        # the UI and the Blender script are data, not importable modules
        "--add-data", f"{os.path.join(ROOT, 'frontend')}{SEP}frontend",
        "--add-data", f"{os.path.join(ROOT, 'backend', 'blender_scripts')}{SEP}backend/blender_scripts",
        # backend modules are imported by name at runtime
        "--paths", os.path.join(ROOT, "backend"),
        "--hidden-import", "main",
        "--hidden-import", "api",
        "--hidden-import", "config",
        "--hidden-import", "core.pipeline",
        "--hidden-import", "core.feature_extractor",
        # uvicorn loads these dynamically, so PyInstaller cannot see them
        "--collect-submodules", "uvicorn",
        "--hidden-import", "uvicorn.logging",
        "--hidden-import", "uvicorn.loops.auto",
        "--hidden-import", "uvicorn.protocols.http.auto",
        "--hidden-import", "uvicorn.protocols.websockets.auto",
        "--hidden-import", "uvicorn.lifespan.on",
        # trimesh resolves format handlers at import time
        "--collect-submodules", "trimesh",
        "--collect-data", "trimesh",
        # keep the build lean: these are only used by the unfinished ML modules
        "--exclude-module", "xgboost",
        "--exclude-module", "sklearn",
        "--exclude-module", "cv2",
        "--exclude-module", "matplotlib",
        "--exclude-module", "tkinter",
        os.path.join(HERE, "app.py"),
    ]

    print("Building", NAME, "...")
    result = subprocess.run(cmd, cwd=ROOT)
    if result.returncode != 0:
        print("Build failed.", file=sys.stderr)
        return result.returncode

    exe = os.path.join(HERE, "dist", f"{NAME}.exe")
    size = os.path.getsize(exe) / (1024 * 1024)
    print(f"\nBuilt {exe} ({size:.0f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
