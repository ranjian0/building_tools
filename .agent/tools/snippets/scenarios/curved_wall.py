"""Scenario: curved wall (180-degree arc, 3m high) -- regression surface for
curved-wall issues (#226 corners, #229 normals, #203 grouped balconies).

Output contract: last line is __JSON__{...} with the inner wall face indices.
"""

import bmesh
import bpy
import json
import math

from mathutils import Vector


def main():
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o)

    me = bpy.data.meshes.new("curved_wall_mesh")
    obj = bpy.data.objects.new("curved_wall", me)
    bpy.context.scene.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj

    bm = bmesh.new()
    seg = 12
    r_out, r_in, height = 5.0, 4.6, 3.0
    ring_out, ring_in = [], []
    for i in range(seg + 1):
        a = math.pi * i / seg  # 0..180 degrees
        ring_out.append(bm.verts.new((r_out * math.cos(a), r_out * math.sin(a), 0)))
        ring_in.append(bm.verts.new((r_in * math.cos(a), r_in * math.sin(a), 0)))
    top_out = [bm.verts.new(v.co + Vector((0, 0, height))) for v in ring_out]
    top_in = [bm.verts.new(v.co + Vector((0, 0, height))) for v in ring_in]

    for i in range(seg):
        bm.faces.new((ring_out[i], ring_out[i + 1], top_out[i + 1], top_out[i]))       # outer
        bm.faces.new((ring_in[i + 1], ring_in[i], top_in[i], top_in[i + 1]))           # inner
        bm.faces.new((ring_in[i], ring_out[i], ring_out[i + 1], ring_in[i + 1]))       # bottom
        bm.faces.new((top_out[i], top_out[i + 1], top_in[i + 1], top_in[i]))           # top
    # end caps
    bm.faces.new((ring_in[0], ring_out[0], top_out[0], top_in[0]))
    bm.faces.new((ring_out[-1], ring_in[-1], top_in[-1], top_out[-1]))
    bm.normal_update()
    bm.to_mesh(me)
    bm.free()

    bm = bmesh.new()
    bm.from_mesh(me)
    bm.faces.ensure_lookup_table()
    inner = []
    for f in bm.faces:
        if abs(f.normal.z) >= 0.1:
            continue
        c = f.calc_center_median()
        radial = Vector((c.x, c.y)).normalized()  # outward radial at face center
        if f.normal.xy.normalized().dot(radial) < -0.9:
            inner.append(f.index)  # normal points toward arc center
    bm.free()

    print("__JSON__" + json.dumps({"object": obj.name, "faces": {"inner": inner}}))


main()
