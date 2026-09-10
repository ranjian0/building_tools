"""Programmatic face selection for presets, facade rules and tooling.

World-space semantics: canonical front = -Y (the side seen from the default
front view and from the reference render camera at (+X, -Y, +Z)). Candidates
are ordered by area (largest first) so singular selectors pick the most
representative face.

Entry points:

    select(obj, selector, floor_height=3.0, storeys=None, group=None)
    top_face(obj)

`storeys` filters band selectors to the given storey indices (0 = ground).
`group` filters by material group name (e.g. "walls") -- faces without the
material-group layer are all eligible.
"""

import bmesh
from mathutils import Vector

FRONT_AXIS = Vector((0.0, -1.0, 0.0))
MATGROUP_LAYER = ".bt_material_group_index"


def _faces(obj, group=None):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.faces.ensure_lookup_table()
    bm.faces.index_update()  # fresh bmeshes have unset (0) indices

    allowed = None
    if group is not None:
        attr = obj.data.attributes.get(MATGROUP_LAYER)
        names = [mt.name for mt in getattr(obj, "bt_materials", [])]
        if attr is not None and group in names:
            target = names.index(group)
            vals = [0] * len(obj.data.polygons)
            attr.data.foreach_get("value", vals)
            allowed = {i for i, v in enumerate(vals) if v == target}
    return bm, allowed


def _sorted_by_area(cands):
    return sorted(cands, key=lambda f: (-f.calc_area(), f.index))


def select(obj, selector, floor_height=3.0, storeys=None, group=None):
    """Resolve a selector name to face indices (see module docstring)."""
    bm, allowed = _faces(obj, group)
    try:
        faces = list(bm.faces)
        top_z = max(f.calc_center_median().z for f in faces)

        def eligible(f):
            return allowed is None or f.index in allowed

        def vertical(f):
            return abs(f.normal.z) < 0.001

        def front(f):
            return f.normal.dot(FRONT_AXIS) > 0.9

        def side(f):
            return abs(f.normal.x) > 0.9

        def back(f):
            return f.normal.dot(FRONT_AXIS) < -0.9

        def big(f):
            return f.calc_area() > 1.0

        def in_storeys(f):
            if storeys is None:
                return True
            z = f.calc_center_median().z
            return any(i * floor_height <= z < (i + 1) * floor_height
                       for i in storeys)

        if selector == "all":
            cands = faces
        elif selector == "top_face":
            cands = [f for f in faces
                     if f.normal.z > 0.9
                     and abs(f.calc_center_median().z - top_z) < 1e-4]
        elif selector in ("front_wall", "front_walls"):
            cands = [f for f in faces if vertical(f) and front(f) and big(f) and in_storeys(f)]
        elif selector in ("side_wall", "side_walls"):
            cands = [f for f in faces if vertical(f) and side(f) and big(f) and in_storeys(f)]
        elif selector in ("back_wall", "back_walls"):
            cands = [f for f in faces if vertical(f) and back(f) and big(f) and in_storeys(f)]
        elif selector in ("walls", "wall"):
            cands = [f for f in faces if vertical(f) and big(f) and in_storeys(f)]
        elif selector in ("ground_front_wall", "ground_front_walls"):
            cands = [f for f in faces
                     if vertical(f) and front(f) and big(f)
                     and f.calc_center_median().z < floor_height]
        elif selector in ("ground_wall", "ground_walls"):
            cands = [f for f in faces
                     if vertical(f) and big(f)
                     and f.calc_center_median().z < floor_height]
        elif selector in ("upper_front_wall", "upper_front_walls"):
            cands = [f for f in faces
                     if vertical(f) and front(f) and big(f)
                     and floor_height < f.calc_center_median().z < top_z - 0.5]
        elif selector in ("upper_wall", "upper_walls"):
            cands = [f for f in faces
                     if vertical(f) and big(f)
                     and floor_height < f.calc_center_median().z < top_z - 0.5]
        elif selector == "inner":
            cands = []
            for f in faces:
                if not vertical(f):
                    continue
                c = f.calc_center_median()
                radial = Vector((c.x, c.y))
                if c.xy.length > 1e-6:
                    radial.normalize()
                if f.normal.xy.dot(radial) < -0.9:
                    cands.append(f)
        else:
            raise RuntimeError("unknown face selector %r" % selector)

        out = [f.index for f in _sorted_by_area(cands) if eligible(f)]
        singular = selector.endswith("_wall") or selector == "top_face"
        return out[:1] if singular else out
    finally:
        bm.free()


def top_face(obj):
    """Largest upward-facing face at the highest z."""
    return select(obj, "top_face")[0]
