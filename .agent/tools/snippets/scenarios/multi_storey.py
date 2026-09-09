"""Scenario: multi-storey building (10 x 8, 3 floors, hip roof), built via the
scriptable api.

Output contract: last line is __JSON__{...} with face groups usable as api
targets (ground/upper wall faces, roof top).
"""

import bmesh
import bpy
import json

from building_tools.btools.api import (
    FaceTarget,
    FloorOptions,
    FloorplanOptions,
    RoofOptions,
    apply_feature,
)


def face_groups(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.faces.ensure_lookup_table()
    bm.faces.index_update()  # fresh bmeshes have unset (0) indices
    top_z = max(f.calc_center_median().z for f in bm.faces)
    groups = {"ground_walls": [], "upper_walls": [], "top_face": []}
    for f in bm.faces:
        c = f.calc_center_median()
        if abs(f.normal.z) > 0.9:
            continue
        if c.z < 3.0 and f.calc_area() > 1.0:
            groups["ground_walls"].append(f.index)
        elif 3.0 < c.z < top_z - 1.5 and f.calc_area() > 1.0:
            groups["upper_walls"].append(f.index)
    cands = [f for f in bm.faces if abs(f.calc_center_median().z - top_z) < 1e-4]
    if cands:
        groups["top_face"] = [max(cands, key=lambda f: f.calc_area()).index]
    bm.free()
    return groups


def main():
    # -- clean scene
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o)

    r = apply_feature("floorplan", FloorplanOptions(width=10.0, length=8.0))
    if not r.ok:
        raise RuntimeError("floorplan failed: %s" % r.errors)
    obj = bpy.data.objects[r.created_object]

    r = apply_feature("floor", FloorOptions(floor_count=3, floor_height=3.0), FaceTarget(obj))
    if not r.ok:
        raise RuntimeError("floors failed: %s" % r.errors)

    groups = face_groups(obj)
    r = apply_feature("roof", RoofOptions(type="HIP", height=1.5), FaceTarget(obj, groups["top_face"]))
    if not r.ok:
        raise RuntimeError("roof failed: %s" % r.errors)
    groups = face_groups(obj)

    print("__JSON__" + json.dumps({"object": obj.name, "faces": groups}))


main()
