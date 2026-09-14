"""Mitered interior offsets derived from a straight skeleton.

One skeleton run yields the inward offset contour(s) at any distance: the
level set at time ``d`` crosses each spanning arc exactly once (at the
wavefront vertex position), and consecutive crossings are joined by
segments lying on the offset lines of the faces between them -- exact
mitered offsets by construction (Palfrader & Held 2015).

Requires the arc face adjacency from ``util_skeleton.Subtree.faces``
(edge ids: edge i ends at contour point i, holes continue the numbering).

Robustness notes: sink times are geometric (distance to the sink's own
flanking edge lines), so merged-vertex birth points and float32 rounding
in the skeleton Vectors do not disturb the level sets; degenerate inputs
(tie-symmetric stars, apses, rings with holes) are closed by the
skeleton's terminal drain before the level-set walk.
"""

import math
from collections import defaultdict

from mathutils import Vector

__all__ = ["offset_polygons"]


def _pt_key(p):
    return (round(p.x, 6), round(p.y, 6))


# -- skeleton points are float32 Vectors while callers pass float64
#    contours; exact key matching straddles rounding boundaries
_BASE_TOL = 1e-5


def _base_matcher(base_points):
    """Fast-ish tolerance membership test for contour points."""
    vectors = [Vector((float(x), float(y))) for x, y in base_points]
    if not vectors:
        return lambda p: False

    def matches(p):
        for v in vectors:
            if (p - v).length <= _BASE_TOL:
                return True
        return False

    return matches


def _signed_area(ring):
    total = 0.0
    n = len(ring)
    for i in range(n):
        x0, y0 = ring[i].x, ring[i].y
        x1, y1 = ring[(i + 1) % n].x, ring[(i + 1) % n].y
        total += x0 * y1 - x1 * y0
    return total / 2.0


def _edge_lines_by_id(base_points):
    """{edge_id: (x0, y0, dx, dy)} unit-direction lines, contour order.

    Edge i runs from base_points[i-1] to base_points[i]; holes continue
    the numbering."""
    lines = {}
    edge_id = 0
    for contour in base_points:
        n = len(contour)
        for i in range(n):
            x0, y0 = contour[i - 1]
            x1, y1 = contour[i]
            dx, dy = x1 - x0, y1 - y0
            length = math.hypot(dx, dy) or 1.0
            lines[edge_id] = (x0, y0, dx / length, dy / length)
            edge_id += 1
    return lines


def _line_distance(p, line):
    x0, y0, dx, dy = line
    return abs((p.x - x0) * dy - (p.y - y0) * dx)


def _as_contours(base_points):
    """A single contour or a list of contours (incl. holes) -> list."""
    if not base_points:
        return []
    first = base_points[0]
    if (
        len(first) == 2
        and isinstance(first[0], (int, float))
        and isinstance(first[1], (int, float))
    ):
        return [base_points]
    return list(base_points)


def offset_polygons(skeleton, base_points, distance):
    """Closed interior offset ring(s) at skeleton-time ``distance``.

    skeleton    -- output of ``btools.utils.skeletonize`` (Subtree list)
    base_points -- the contour(s) the skeleton was built from (a single
                   contour or a list of contours incl. holes); outline
                   edge i ends at contour point i
    distance    -- offset distance in the skeleton's time units

    Returns a list of rings (lists of 2D points, clockwise like the input);
    empty when the offset is at or beyond the skeleton's max height.
    """
    if distance <= 0.0:
        raise ValueError("offset distance must be positive")
    contours = _as_contours(base_points)
    on_base = _base_matcher([pt for c in contours for pt in c])
    lines = _edge_lines_by_id(contours)

    def sink_time(s, faces):
        """A sink's time is geometric: its distance to its own flanking
        edge lines (0 on the outline; the birth time of merged vertices --
        independent of arc bookkeeping and float32 rounding)."""
        ds = [_line_distance(s, lines[e]) for e in faces if e in lines]
        return min(ds) if ds else 0.0

    sink_h = {}
    for arc in skeleton:
        for s, faces in zip(arc.sinks, arc.faces):
            k = _pt_key(s)
            if on_base(s):
                sink_h[k] = 0.0
            else:
                t = sink_time(s, faces)
                sink_h[k] = min(sink_h.get(k, math.inf), t)

    # -- crossings on arcs spanning `distance`, tagged with flanking faces
    crossings = []  # (point, face_a, face_b)
    for arc in skeleton:
        t_src = arc.height
        for s, faces in zip(arc.sinks, arc.faces):
            t_snk = sink_h[_pt_key(s)]
            lo, hi = (t_snk, t_src) if t_snk < t_src else (t_src, t_snk)
            if not (lo < distance < hi):
                continue
            f = (distance - t_snk) / (t_src - t_snk)
            f = min(max(f, 0.0), 1.0)
            crossings.append((s + (arc.source - s) * f, faces[0], faces[1]))

    if not crossings:
        return []

    # -- edge geometry for projection ordering (edge i runs from
    #    contour[i-1] to contour[i]; holes continue the numbering)
    edges = lines

    # -- per-face segments: a face's crossings are paired consecutively
    #    along its edge direction (a face crossed 2k times contributes k
    #    segments); rings are the cycles of the crossing graph
    by_face = defaultdict(list)
    for idx, (_pt, f0, f1) in enumerate(crossings):
        by_face[f0].append(idx)
        by_face[f1].append(idx)

    adj = defaultdict(set)
    for face_id, idxs in by_face.items():
        if len(idxs) < 2 or face_id not in edges:
            continue
        ex, ey, edx, edy = edges[face_id]
        idxs.sort(
            key=lambda i: (
                (crossings[i][0].x - ex) * edx + (crossings[i][0].y - ey) * edy
            )
        )
        for a, b in zip(idxs[0::2], idxs[1::2]):
            pti, ptj = crossings[a][0], crossings[b][0]
            if (pti - ptj).length < 1e-9:
                continue  # zero-length segment at a coincident event point
            adj[a].add(b)
            adj[b].add(a)

    rings = []
    visited = set()
    for start in sorted(adj):
        if start in visited or len(adj[start]) != 2:
            continue
        walk = [start]
        visited.add(start)
        prev, cur = None, start
        while True:
            nxts = (adj[cur] - {prev}) if prev is not None else adj[cur]
            nxts = {n for n in nxts if n not in visited or n == start}
            if not nxts:
                break
            nxt = min(nxts)  # deterministic walks
            if nxt == start:
                break  # ring closed
            walk.append(nxt)
            visited.add(nxt)
            prev, cur = cur, nxt
        if len(walk) >= 3:
            ring = [crossings[i][0] for i in walk]
            if _signed_area(ring) > 0.0:
                ring.reverse()  # match the input's clockwise winding
            rings.append(ring)
    return rings
