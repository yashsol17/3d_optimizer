"""
Unreal Editor script: optimize the selected Static Meshes through the service.

Select one or more Static Mesh assets in the Content Browser, then run:

    Tools > Execute Python Script...  ->  optimize_selected.py

Each mesh is exported to glTF, sent to the optimization service, and the
decimated result is imported back into /Game/Optimized as a new asset, so the
original is never modified.

Requirements inside the editor:
  * "Python Editor Script Plugin"  (Edit > Plugins)
  * "glTF Exporter" plugin         (ships with UE5, enable it)
  * Interchange glTF import, on by default in UE 5.1+

Configure with environment variables or by editing the constants below:
  MESH_OPTIMIZER_URL   service address  (default http://127.0.0.1:8000)
  MESH_OPTIMIZER_KEY   X-API-Key value, if the service requires one

NOTE: this script has not been run against a live editor — no Unreal install
was available where it was written. Treat the first run as a test: it only
writes new assets under DESTINATION_PATH, but verify on a scratch project.
"""
import os
import sys
import tempfile

import unreal

# --------------------------------------------------------------- settings
SERVICE_URL = os.environ.get("MESH_OPTIMIZER_URL", "http://127.0.0.1:8000")
API_KEY = os.environ.get("MESH_OPTIMIZER_KEY")
RATIO = 0.35                      # keep 35% of the faces
DESTINATION_PATH = "/Game/Optimized"
SUFFIX = "_LOD"

# The client module lives next to this file
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "python"))
from mesh_optimizer import optimize_file, OptimizerError  # noqa: E402


def log(message: str) -> None:
    unreal.log(f"[MeshOptimizer] {message}")


def export_to_gltf(asset, directory: str) -> str | None:
    """Export a Static Mesh asset to a .glb file on disk."""
    path = os.path.join(directory, f"{asset.get_name()}.glb")

    task = unreal.AssetExportTask()
    task.object = asset
    task.filename = path
    task.automated = True          # no dialogs
    task.prompt = False
    task.replace_identical = True
    try:
        task.options = unreal.GLTFExportOptions()
    except AttributeError:
        log("glTF Exporter plugin not enabled — enable it in Edit > Plugins.")
        return None

    if not unreal.Exporter.run_asset_export_task(task):
        log(f"Export failed for {asset.get_name()}")
        return None
    return path if os.path.exists(path) else None


def import_back(glb_path: str, asset_name: str):
    """Import the optimized mesh as a new asset under DESTINATION_PATH."""
    task = unreal.AssetImportTask()
    task.filename = glb_path
    task.destination_path = DESTINATION_PATH
    task.destination_name = f"{asset_name}{SUFFIX}"
    task.automated = True
    task.replace_existing = True
    task.save = True

    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    return list(task.get_editor_property("imported_object_paths") or [])


def run() -> None:
    selected = unreal.EditorUtilityLibrary.get_selected_assets()
    meshes = [a for a in selected if isinstance(a, unreal.StaticMesh)]

    if not meshes:
        log("Select one or more Static Mesh assets in the Content Browser first.")
        return

    log(f"Optimizing {len(meshes)} mesh(es) at ratio {RATIO} via {SERVICE_URL}")
    workdir = tempfile.mkdtemp(prefix="mesh_opt_")
    succeeded, failed = 0, 0

    with unreal.ScopedSlowTask(len(meshes), "Optimizing meshes") as task:
        task.make_dialog(True)
        for asset in meshes:
            if task.should_cancel():
                break
            name = asset.get_name()
            task.enter_progress_frame(1, f"Optimizing {name}")

            exported = export_to_gltf(asset, workdir)
            if not exported:
                failed += 1
                continue

            out_path = os.path.join(workdir, f"{name}_optimized.glb")
            try:
                report = optimize_file(
                    exported, out_path=out_path, ratio=RATIO,
                    url=SERVICE_URL, api_key=API_KEY,
                )
            except OptimizerError as exc:
                log(f"{name}: {exc}")
                failed += 1
                continue

            imported = import_back(out_path, name)
            if imported:
                succeeded += 1
                log(f"{name}: {report['original_faces']:,} -> {report['optimized_faces']:,} faces "
                    f"({report['polygon_reduction_percent']}% removed) -> {imported[0]}")
            else:
                failed += 1
                log(f"{name}: optimized but the reimport produced no asset")

    log(f"Done. {succeeded} optimized, {failed} failed. New assets in {DESTINATION_PATH}")


if __name__ == "__main__":
    run()
