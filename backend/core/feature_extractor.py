import trimesh
import numpy as np

def extract_mesh_features(file_path: str) -> dict:
    """
    Extracts geometric and topological features from a 3D model.
    """
    scene_or_mesh = trimesh.load(file_path)
    
    # Handle both single meshes and complex scene graphs
    if isinstance(scene_or_mesh, trimesh.Scene):
        mesh = scene_or_mesh.dump(concatenate=True)
    else:
        mesh = scene_or_mesh

    bounds = mesh.extents  # Bounding box dimensions [x, y, z]
    
    features = {
        "vertex_count": int(len(mesh.vertices)),
        "face_count": int(len(mesh.faces)),
        "surface_area": float(mesh.area),
        "volume": float(mesh.volume) if mesh.is_volume else 0.0,
        "is_watertight": bool(mesh.is_watertight),
        "bounding_box_x": float(bounds[0]),
        "bounding_box_y": float(bounds[1]),
        "bounding_box_z": float(bounds[2]),
        "aspect_ratio": float(max(bounds) / (min(bounds) + 1e-6))
    }
    
    return features

if __name__ == "__main__":
    # Test script locally
    import sys
    if len(sys.argv) > 1:
        print(extract_mesh_features(sys.argv[1]))