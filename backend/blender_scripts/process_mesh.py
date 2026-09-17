import bpy
import sys
import argparse
import os

def parse_args():
    try:
        idx = sys.argv.index("--")
        args = sys.argv[idx + 1:]
    except ValueError:
        args = []
    
    parser = argparse.ArgumentParser(description="Blender Mesh Processor")
    parser.add_argument("--input", required=True, help="Path to input GLB file")
    parser.add_argument("--output", required=True, help="Path to output GLB file")
    parser.add_argument("--ratio", type=float, default=0.35, help="Decimation ratio (0.1 to 1.0)")
    return parser.parse_args(args)

def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)

def import_model(filepath):
    ext = os.path.splitext(filepath)[1].lower()
    if ext in ['.glb', '.gltf']:
        if hasattr(bpy.ops.import_scene, 'gltf'):
            bpy.ops.import_scene.gltf(filepath=filepath)
        elif hasattr(bpy.ops.wm, 'gltf_import'):
            bpy.ops.wm.gltf_import(filepath=filepath)
    elif ext == '.fbx':
        bpy.ops.import_scene.fbx(filepath=filepath)
    elif ext == '.obj':
        if hasattr(bpy.ops.wm, 'obj_import'):
            bpy.ops.wm.obj_import(filepath=filepath)
        elif hasattr(bpy.ops.import_scene, 'obj'):
            bpy.ops.import_scene.obj(filepath=filepath)

def process_and_decimate(ratio):
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
    
    for obj in meshes:
        bpy.context.view_layer.objects.active = obj
        
        # 1. Cleanup loose geometry and fix normals
        try:
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.mesh.remove_doubles(threshold=0.0001)
            bpy.ops.mesh.normals_make_consistent(inside=False)
            bpy.ops.object.mode_set(mode='OBJECT')
        except Exception as e:
            print(f"Cleanup warning on {obj.name}: {e}")
            if bpy.context.object and bpy.context.object.mode != 'OBJECT':
                bpy.ops.object.mode_set(mode='OBJECT')
        
        # 2. Apply Decimate Modifier (Fixed attribute name)
        dec_mod = obj.modifiers.new(name="AutoDecimate", type='DECIMATE')
        dec_mod.decimate_type = 'COLLAPSE'
        dec_mod.ratio = ratio
        bpy.ops.object.modifier_apply(modifier=dec_mod.name)

def export_model(filepath):
    if hasattr(bpy.ops.export_scene, 'gltf'):
        bpy.ops.export_scene.gltf(filepath=filepath, export_format='GLB', export_apply=True)
    elif hasattr(bpy.ops.wm, 'gltf_export'):
        bpy.ops.wm.gltf_export(filepath=filepath, export_format='GLB', export_apply=True)
    else:
        raise RuntimeError("No suitable GLTF export operator found in Blender.")

def main():
    args = parse_args()
    clear_scene()
    print(f"Importing: {args.input}")
    import_model(args.input)
    print(f"Processing Decimation with ratio {args.ratio}...")
    process_and_decimate(args.ratio)
    print(f"Exporting to: {args.output}")
    export_model(args.output)
    print("Optimization Completed Successfully.")

if __name__ == "__main__":
    main()