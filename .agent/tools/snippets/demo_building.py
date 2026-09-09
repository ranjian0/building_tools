"""End-to-end demo on the scriptable api: floorplan -> 3 floors -> hip roof
-> door -> window, then structured validation.

Equivalent to a user modeling a complete building; serves as the regression
reference for the api surface. Run: `bt exec demo_building.py`.
"""

import bmesh
import bpy
import json

from building_tools.btools.api import (
    DoorOptions,
    FaceTarget,
    FloorOptions,
    FloorplanOptions,
    RoofOptions,
    WindowOptions,
    apply_feature,
)
from building_tools.btools.api.validate import validate_object


def clean_scene():
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o)


def wall_faces(obj, zmin, zmax):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    picked = [
        f.index
        for f in bm.faces
        if abs(f.normal.z) < 0.001
        and zmin < f.calc_center_median().z < zmax
        and f.calc_area() > 1.0
    ]
    bm.free()
    return picked


def top_face(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.faces.ensure_lookup_table()
    top_z = max(f.calc_center_median().z for f in bm.faces)
    cands = [f for f in bm.faces if abs(f.calc_center_median().z - top_z) < 1e-4]
    idx = max(cands, key=lambda f: f.calc_area()).index
    bm.free()
    return idx


def run(feature, options, target=None):
    res = apply_feature(feature, options, target)
    print("  %-10s -> %s %s" % (feature, res.status, res.matgroup_counts or res.errors))
    if not res.ok:
        raise SystemExit("%s failed: %s" % (feature, res.errors))
    return res


def main():
    clean_scene()

    print("[demo] building via api...")
    res = run("floorplan", FloorplanOptions(width=10.0, length=8.0))
    obj = bpy.data.objects[res.created_object]

    run("floor", FloorOptions(floor_count=3, floor_height=3.0), FaceTarget(obj))
    run("roof", RoofOptions(type="HIP", height=1.5), FaceTarget(obj, [top_face(obj)]))
    run("door", DoorOptions(), FaceTarget(obj, wall_faces(obj, 0.0, 3.0)))
    run("window", WindowOptions(), FaceTarget(obj, wall_faces(obj, 3.0, 6.0)))

    report = validate_object(
        obj,
        expect={"groups": ["walls", "roof", "slabs", "door", "frame", "window"]},
        include_geometry=False,  # door/window frame seams are advisory (known)
    )
    print("[demo] validate: ok=%s problems=%s" % (report["ok"], report["problems"]))
    print(
        "__JSON__" + json.dumps({
            "object": obj.name,
            "faces": len(obj.data.polygons),
            "verts": len(obj.data.vertices),
            "valid": report["ok"],
            "problems": report["problems"],
        })
    )


main()
