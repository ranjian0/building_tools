"""Programmatic face selection for scenarios and reference sweeps.

Runs inside the Blender session (exec'd by reference_sweep.py, which injects
this file's content). One entry point:

    select(obj, selector) -> [face indices]

Selectors describe WHERE an element belongs in world space (canonical front
= +Y, the side the render camera sees); candidates are ordered by area
(largest first) so singular selectors pick the most representative face.
"""

import bmesh
from mathutils import Vector

FRONT_AXIS = Vector((0.0, -1.0, 0.0))  # canonical "front" faces -Y (the side
                                       # the render camera at (+1, -1, +z) sees)


def _faces(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.faces.ensure_lookup_table()
    bm.faces.index_update()  # fresh bmeshes have unset (0) indices
    return bm


def _sorted_by_area(cands):
    return sorted(cands, key=lambda f: (-f.calc_area(), f.index))


def select(obj, selector):
    bm = _faces(obj)
    try:
        faces = list(bm.faces)
        top_z = max(f.calc_center_median().z for f in faces)

        def vertical(f):
            return abs(f.normal.z) < 0.001

        def front(f):
            return f.normal.dot(FRONT_AXIS) > 0.9

        def ground(f):
            return f.calc_center_median().z < 3.0

        def upper(f):
            return 3.0 < f.calc_center_median().z < top_z - 0.5

        def big(f):
            return f.calc_area() > 1.0

        if selector == "all":
            cands = faces
        elif selector == "top_face":
            cands = [f for f in faces
                     if f.normal.z > 0.9
                     and abs(f.calc_center_median().z - top_z) < 1e-4]
        elif selector in ("front_wall", "front_walls"):
            cands = [f for f in faces if vertical(f) and front(f) and big(f)]
        elif selector in ("ground_front_wall", "ground_front_walls"):
            cands = [f for f in faces if vertical(f) and front(f) and big(f) and ground(f)]
        elif selector in ("upper_front_wall", "upper_front_walls"):
            cands = [f for f in faces if vertical(f) and front(f) and big(f) and upper(f)]
        elif selector in ("ground_walls", "ground_wall"):
            cands = [f for f in faces if vertical(f) and big(f) and ground(f)]
        elif selector in ("upper_walls", "upper_wall"):
            cands = [f for f in faces if vertical(f) and big(f) and upper(f)]
        elif selector == "inner":
            cands = []
            for f in faces:
                if vertical(f):
                    c = f.calc_center_median()
                    radial = Vector((c.x, c.y))
                    if c.xy.length > 1e-6:
                        radial.normalize()
                    if f.normal.xy.dot(radial) < -0.9:
                        cands.append(f)
        else:
            raise RuntimeError("unknown face selector %r" % selector)

        out = [f.index for f in _sorted_by_area(cands)]
        singular = selector.endswith("_wall") or selector == "top_face"
        return out[:1] if singular else out
    finally:
        bm.free()
