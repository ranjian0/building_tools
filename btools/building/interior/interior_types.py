"""Interior partition generation (roadmap item 7, phases 2-3).

Two subdivision modes over a floor face's footprint:

- TREEMAP (rooms): squarified treemap (Bruls et al.) over the inner
  bounding rectangle; partition walls run along shared room borders;
  doors come from a spanning tree of the room adjacency graph (minimum
  doors preserving reachability).
- SKELETON (corridor): straight-skeleton arcs deeper than
  ``min_corridor`` become a medial-axis corridor wall, splitting the
  floor into wings; a door sits at each arc's midpoint.

Walls are closed boxes (sides + top) standing on the target face; doors
are full-width gaps with a header face filling ``door_height`` up to the
partition height.
"""

import math

from ...utils import (
    Rect as LayoutRect,
)
from ...utils import (
    adjacency_segments,
    offset_polygons,
    skeletonize,
    spanning_doors,
    squarify,
)
from ..floor.floor_types import _face_contour
from ..materialgroup import MaterialGroup, add_faces_to_group


def create_partitions(bm, faces, prop):
    """Create interior partitions from an upward-facing floor face."""
    face = faces[-1]
    contour = _face_contour(face)

    inset = getattr(prop, "inset", 0.0)
    if inset > 0.0:
        skeleton = skeletonize(contour, [])
        rings = offset_polygons(skeleton, contour, inset)
        if rings:
            contour = [(p.x, p.y) for p in max(rings, key=_ring_area)]

    z0 = face.calc_center_median().z
    height = prop.partition_height
    thickness = prop.partition_thickness

    if prop.partition_mode == "SKELETON":
        segments = _corridor_segments(contour, prop.min_corridor)
        doors = [((0, 1), _segment_midpoint(seg)) for seg in segments]
    else:
        segments, doors = _room_segments(contour, prop)

    walls = []
    for seg in segments:
        walls.extend(
            _build_walls_with_doors(bm, seg, z0, height, thickness, prop, doors)
        )

    add_faces_to_group(bm, walls, MaterialGroup.WALLS)
    return walls


def _ring_area(ring):
    area = 0.0
    n = len(ring)
    for i in range(n):
        x0, y0 = ring[i - 1].x, ring[i - 1].y
        x1, y1 = ring[i].x, ring[i].y
        area += x0 * y1 - x1 * y0
    return abs(area) / 2.0


def _segment_midpoint(seg):
    (x0, y0), (x1, y1) = seg
    return ((x0 + x1) / 2.0, (y0 + y1) / 2.0)


def _corridor_segments(contour, min_corridor):
    """Core/perimeter walls: the level-set ring at ``min_corridor`` depth
    (the medial-axis corridor loop -- Honeybee-style core + ring)."""
    skeleton = skeletonize(contour, [])
    rings = offset_polygons(skeleton, contour, min_corridor)
    segments = []
    for ring in rings:
        n = len(ring)
        for i in range(n):
            seg = ((ring[i - 1].x, ring[i - 1].y), (ring[i].x, ring[i].y))
            if _seg_length(seg) > 0.05:
                segments.append(seg)
    return segments


def _room_segments(contour, prop):
    """Treemap room walls (shared borders) and their spanning-tree doors."""
    xs = [x for x, _ in contour]
    ys = [y for _, y in contour]
    rect = LayoutRect(min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))

    count = max(2, int(getattr(prop, "room_count", 4)))
    rects = squarify(rect, [1.0] * count)
    if len(rects) < 2:
        return [], []

    segments = [
        seg for _pair, seg in adjacency_segments(rects) if _seg_length(seg) > 0.05
    ]
    doors = spanning_doors(adjacency_segments(rects), prop.door_width)
    return segments, doors


def _seg_length(seg):
    (x0, y0), (x1, y1) = seg
    return math.hypot(x1 - x0, y1 - y0)


def _match_doors(seg, doors):
    """Doors lying on ``seg`` (within tolerance), as (point, width)."""
    out = []
    (x0, y0), (x1, y1) = seg
    for _pair, (px, py) in doors:
        # -- point on segment: between endpoints and within line distance
        cross = (px - x0) * (y1 - y0) - (py - y0) * (x1 - x0)
        length = _seg_length(seg)
        if length == 0 or abs(cross) / length > 1e-3:
            continue
        t = ((px - x0) * (x1 - x0) + (py - y0) * (y1 - y0)) / (length * length)
        if -1e-6 <= t <= 1.0 + 1e-6:
            out.append(t)
    return out


def _build_walls_with_doors(bm, seg, z0, height, thickness, prop, doors):
    """Wall boxes along ``seg``, split at door positions; doors get a
    header from door_height to partition_height."""
    (x0, y0), (x1, y1) = seg
    length = _seg_length(seg)
    if length < 1e-6:
        return []

    door_ts = sorted(_match_doors(seg, doors))
    half = prop.door_width / 2.0
    walls = []
    cuts = [0.0]
    for t in door_ts:
        w = min(half / length, 0.45)  # keep the door inside the segment
        cuts.extend([max(0.0, t - w), min(1.0, t + w)])
    cuts.append(1.0)
    cuts = sorted(set(round(c, 9) for c in cuts))

    for a, b in zip(cuts[0::2], cuts[1::2]):
        # wall piece between cuts (full height)
        pa = (x0 + (x1 - x0) * a, y0 + (y1 - y0) * a)
        pb = (x0 + (x1 - x0) * b, y0 + (y1 - y0) * b)
        if _seg_length((pa, pb)) > 1e-6:
            walls.extend(_build_wall_box(bm, pa, pb, z0, height, thickness))

    for a, b in zip(cuts[1::2], cuts[2::2] if len(cuts) > 2 else []):
        # door span: header from door_height to partition height
        pa = (x0 + (x1 - x0) * a, y0 + (y1 - y0) * a)
        pb = (x0 + (x1 - x0) * b, y0 + (y1 - y0) * b)
        if _seg_length((pa, pb)) > 1e-6 and prop.door_height < height:
            walls.extend(
                _build_wall_box(
                    bm,
                    pa,
                    pb,
                    z0 + prop.door_height,
                    height - prop.door_height,
                    thickness,
                )
            )
    return walls


def _build_wall_box(bm, pa, pb, z0, height, thickness):
    """Closed wall box between 2D points pa-pb, from z0 to z0+height."""
    dx, dy = pb[0] - pa[0], pb[1] - pa[1]
    length = math.hypot(dx, dy)
    if length == 0.0:
        return []
    nx, ny = -dy / length * (thickness / 2.0), dx / length * (thickness / 2.0)

    bottom = [
        bm.verts.new((pa[0] + nx, pa[1] + ny, z0)),
        bm.verts.new((pb[0] + nx, pb[1] + ny, z0)),
        bm.verts.new((pb[0] - nx, pb[1] - ny, z0)),
        bm.verts.new((pa[0] - nx, pa[1] - ny, z0)),
    ]
    top = [bm.verts.new((v.co.x, v.co.y, z0 + height)) for v in bottom]

    faces = []
    n = 4
    for i in range(n):
        j = (i + 1) % n
        faces.append(bm.faces.new((bottom[i], bottom[j], top[j], top[i])))
    faces.append(bm.faces.new(list(reversed(top))))
    return faces
