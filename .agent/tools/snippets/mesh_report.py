"""Report on the active mesh object: counts, material-group face table,
and common geometry problems (non-manifold edges, loose geometry, untagged
faces, zero-area faces).

The material-group table is the main validation surface for the addon:
every generated face should belong to exactly one group.
"""

import bpy
import bmesh
from collections import Counter


def main():
    obj = bpy.context.object
    if obj is None or obj.type != "MESH":
        raise RuntimeError("active object is not a mesh")

    me = obj.data
    bm = bmesh.from_edit_mesh(me) if obj.mode == "EDIT" else bmesh.new()
    if obj.mode != "EDIT":
        bm.from_mesh(me)

    print("object: %s (mode=%s)" % (obj.name, obj.mode))
    print("verts: %d  edges: %d  faces: %d" % (len(bm.verts), len(bm.edges), len(bm.faces)))

    # -- material groups
    layer = bm.faces.layers.int.get(".bt_material_group_index")
    groups = [mt.name for mt in obj.bt_materials]
    if layer:
        counts = Counter(f[layer] for f in bm.faces)
        total_tagged = 0
        print("material groups:")
        for idx, name in enumerate(groups):
            n = counts.get(idx, 0)
            total_tagged += n
            print("  [%2d] %-18s %6d" % (idx, name, n))
        unknown = sum(n for i, n in counts.items() if i >= len(groups))
        if unknown:
            print("  [??] %-18s %6d  (index out of range -- corrupted matgroups)" % ("?", unknown))
        untagged = len(bm.faces) - total_tagged - unknown
        if untagged:
            print("  !! %d faces with NO material group" % untagged)
        else:
            print("  all faces tagged (%d groups)" % len(groups))
    else:
        print("  no .bt_material_group_index layer on this mesh")

    # -- geometry problems
    nonmanifold = [e for e in bm.edges if not e.is_manifold]
    loose_v = [v for v in bm.verts if not v.link_edges]
    loose_e = [e for e in bm.edges if not e.link_faces]
    zero_area = [f for f in bm.faces if f.calc_area() < 1e-9]

    def report(label, items):
        if items:
            print("  !! %-22s %d" % (label, len(items)))

    print("checks:")
    if not nonmanifold and not loose_v and not loose_e and not zero_area:
        print("  clean: no non-manifold edges, loose geometry, or zero-area faces")
    report("non-manifold edges", nonmanifold)
    report("loose verts", loose_v)
    report("loose edges", loose_e)
    report("zero-area faces", zero_area)

    if obj.mode != "EDIT":
        bm.free()


main()
