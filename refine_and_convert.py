"""
Refine and convert GLB files from ComfyUI output to card directory.
Handles the work that the n8n Refine 3D Meshes + Convert GLB to OBJ nodes
would have done, but outside n8n to avoid task runner memory issues.

Steps per model:
  1. Copy GLB from ComfyUI output to card dir
  2. Refine with trimesh: clean, decimate, smooth, fix normals
  3. Convert to OBJ
"""

import os
import sys
import gc
import trimesh
import numpy as np

COMFY_OUTPUT = "D:/ComfyUI_windows_portable/ComfyUI/output"
CARD_DIR = "D:/data/cards/Standard/Cards"

def find_source_glb(prefix):
    """Find the GLB in ComfyUI output matching prefix, checking both root and mesh/ subfolder."""
    for search_dir in [COMFY_OUTPUT, os.path.join(COMFY_OUTPUT, "mesh")]:
        if not os.path.isdir(search_dir):
            continue
        matches = sorted(
            [f for f in os.listdir(search_dir) if f.startswith(prefix) and f.endswith(".glb")],
            reverse=True,
        )
        if matches:
            return os.path.join(search_dir, matches[0])
    return None


def refine_mesh(glb_path):
    """Load, clean, decimate, smooth, fix normals, and re-export a GLB."""
    m = trimesh.load(glb_path)
    if hasattr(m, "geometry") and isinstance(m.geometry, dict):
        m = trimesh.util.concatenate(list(m.geometry.values()))

    # trimesh 4.x API: use nondegenerate_faces mask instead of removed methods
    mask = m.nondegenerate_faces()
    if not mask.all():
        m.update_faces(mask)
    m.remove_unreferenced_vertices()
    m.fill_holes()

    target_faces = 50000
    if len(m.faces) > target_faces:
        try:
            m = m.simplify_quadric_decimation(target_faces)
        except Exception:
            pass

    try:
        trimesh.smoothing.filter_laplacian(m, iterations=5)
    except Exception:
        pass

    m.fix_normals()
    stats = f"faces={len(m.faces)} verts={len(m.vertices)} watertight={m.is_watertight}"
    m.export(glb_path)
    return stats


def convert_to_obj(glb_path, obj_path):
    """Convert GLB to OBJ format."""
    m = trimesh.load(glb_path)
    if hasattr(m, "geometry") and isinstance(m.geometry, dict):
        m = trimesh.util.concatenate(list(m.geometry.values()))
    m.export(obj_path)


def main():
    # Build list of what needs processing
    existing_glb = set(f for f in os.listdir(CARD_DIR) if f.startswith("MODEL_") and f.endswith(".glb"))
    existing_obj = set(f for f in os.listdir(CARD_DIR) if f.startswith("MODEL_") and f.endswith(".obj"))

    # Find all GLBs in ComfyUI output
    comfy_glbs = {}
    for search_dir in [COMFY_OUTPUT, os.path.join(COMFY_OUTPUT, "mesh")]:
        if not os.path.isdir(search_dir):
            continue
        for f in os.listdir(search_dir):
            if f.startswith("MODEL_") and f.endswith(".glb"):
                # Normalize: MODEL_Ace_of_Cups_between_00001_.glb -> MODEL_Ace_of_Cups_between
                base = f.rsplit("_0000", 1)[0]
                canonical = base + ".glb"
                if canonical not in comfy_glbs:
                    comfy_glbs[canonical] = os.path.join(search_dir, f)

    # Determine what needs work
    need_refine = []
    need_obj_only = []
    for canonical, source_path in sorted(comfy_glbs.items()):
        obj_name = canonical.replace(".glb", ".obj")
        glb_exists = canonical in existing_glb
        obj_exists = obj_name in existing_obj

        if not glb_exists:
            need_refine.append((canonical, source_path, obj_name))
        elif not obj_exists:
            need_obj_only.append((canonical, os.path.join(CARD_DIR, canonical), obj_name))

    total = len(need_refine) + len(need_obj_only)
    print(f"Need refine+copy+OBJ: {len(need_refine)}")
    print(f"Need OBJ only: {len(need_obj_only)}")
    print(f"Total to process: {total}")
    print()

    done = 0
    failed = 0

    # Process models needing full refine
    for canonical, source_path, obj_name in need_refine:
        done += 1
        dest_glb = os.path.join(CARD_DIR, canonical)
        dest_obj = os.path.join(CARD_DIR, obj_name)
        tag = f"[{done}/{total}]"

        try:
            # Copy to card dir
            import shutil
            shutil.copy2(source_path, dest_glb)

            # Refine
            stats = refine_mesh(dest_glb)
            glb_kb = os.path.getsize(dest_glb) // 1024

            # Convert to OBJ
            convert_to_obj(dest_glb, dest_obj)
            obj_kb = os.path.getsize(dest_obj) // 1024

            print(f"{tag} OK {canonical} ({glb_kb}KB GLB, {obj_kb}KB OBJ) {stats}")
        except Exception as e:
            failed += 1
            print(f"{tag} FAIL {canonical}: {e}", file=sys.stderr)

        # Force garbage collection to prevent memory buildup
        gc.collect()

    # Process models needing OBJ only
    for canonical, glb_path, obj_name in need_obj_only:
        done += 1
        dest_obj = os.path.join(CARD_DIR, obj_name)
        tag = f"[{done}/{total}]"

        try:
            convert_to_obj(glb_path, dest_obj)
            obj_kb = os.path.getsize(dest_obj) // 1024
            print(f"{tag} OBJ {canonical} ({obj_kb}KB)")
        except Exception as e:
            failed += 1
            print(f"{tag} FAIL OBJ {canonical}: {e}", file=sys.stderr)

        gc.collect()

    print(f"\nDone: {done - failed} succeeded, {failed} failed out of {total}")


if __name__ == "__main__":
    main()
