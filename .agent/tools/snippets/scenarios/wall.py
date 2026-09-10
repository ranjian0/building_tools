"""Scenario: single straight wall (6 x 3, thickness 0.4).

Returns a wall mesh with named face groups for api operations.
Output contract: last line is __JSON__{...}.
"""

import bmesh
import bpy
import json


def main():
    # -- clean scene
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o)

    me = bpy.data.meshes.new("wall_mesh")
    obj = bpy.data.objects.new("wall", me)
    bpy.context.scene.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj

    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = (v.co.x * 6.0, v.co.y * 0.4, (v.co.z + 0.5) * 3.0)
    bm.normal_update()
    bm.to_mesh(me)
    bm.free()

    bm = bmesh.new()
    bm.from_mesh(me)
    bm.faces.ensure_lookup_table()
    faces = {"front": [], "back": [], "top": [], "sides": [], "bottom": []}
    for f in bm.faces:
        n = f.normal
        c = f.calc_center_median()
        if abs(n.z) > 0.9:
            faces["top" if n.z > 0 else "bottom"].append(f.index)
        elif abs(n.y) > 0.9:
            faces["front" if n.y < 0 else "back"].append(f.index)
        else:
            faces["sides"].append(f.index)
    bm.free()

    print("__JSON__" + json.dumps({"object": obj.name, "faces": faces}))


main()
