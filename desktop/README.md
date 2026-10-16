# Windows desktop application

`MeshOptimizer.exe` is the same application as the web build, wrapped in a native
window. It starts the FastAPI service in-process on a free local port and shows
the existing interface — one codebase, two shells.

## Build

```bash
.venv\Scripts\python.exe -m pip install pywebview pyinstaller
.venv\Scripts\python.exe desktop\build.py
```

Output: `desktop/dist/MeshOptimizer.exe` — a single file, about 62 MB, that runs
on any Windows 10/11 machine with **no Python installed**.

## What the app needs on the target machine

| Requirement | Notes |
|---|---|
| Windows 10 or 11 (64-bit) | Built and tested on Windows 11 |
| Blender | **Not bundled** — it is a ~1 GB application with its own installer |
| Python | Not required; the runtime is inside the exe |

Blender is found automatically: the app scans the usual install locations
(Program Files, LocalAppData, Steam) and picks the newest version. Set the
`BLENDER_PATH` environment variable to override. If Blender is missing, the app
still opens and says so instead of failing silently when you press Run.

## Where data goes

A packaged app may sit in a read-only folder, so user data lives in:

```
%LOCALAPPDATA%\MeshOptimizer\storage\   uploaded and optimized models
%LOCALAPPDATA%\MeshOptimizer\startup.log   startup diagnostics
```

A windowed build has no console, so the log is the place to look when something
goes wrong on another machine.

## Files

| File | Purpose |
|---|---|
| `app.py` | Launcher: starts the server, waits for health, opens the window |
| `build.py` | PyInstaller build with the data files and hidden imports it needs |
| `make_icon.py` | Generates `icon.ico` |

## Notes for packaging

- `--windowed` means `sys.stdout` and `sys.stderr` are `None`. Anything that
  touches them crashes at startup, so the launcher replaces them and uvicorn is
  configured with `log_config=None`.
- `xgboost`, `scikit-learn` and OpenCV are excluded from the build — they are
  pulled in by `requirements.txt` for the unfinished ML modules and would add
  hundreds of megabytes for nothing.
- A running copy locks the exe; close the app before rebuilding.
