"""Mitered interior offsets derived from a straight skeleton.

One skeleton run yields the inward offset contour(s) at any distance: the
level set at time ``d`` crosses each spanning arc exactly once (at the
wavefront vertex position), and consecutive crossings are joined by
segments lying on the offset lines of the faces between them -- exact
mitered offsets by construction (Palfrader & Held 2015).

Requires the arc face adjacency from ``util_skeleton.Subtree.faces``
(edge ids: edge i ends at contour point i, holes continue the numbering).
"""

import math
from collections import defaultdict

__all__ = ["offset_polygons"]


def _pt_key(p):
    return (round(p.x, 6), round(p.y, 6))


def _signed_area(ring):
    total = 0.0
    n = len(ring)
    for i in range(n):
        x0, y0 = ring[i].x, ring[i].y
        x1, y1 = ring[(i + 1) % n].x, ring[(i + 1) % n].y
        total += x0 * y1 - x1 * y0
    return total / 2.0


def offset_polygons(skeleton, base_points, distance):
    """Closed interior offset ring(s) at skeleton-time ``distance``.

    skeleton    -- output of ``btools.utils.skeletonize`` (Subtree list)
    base_points -- the contour points the skeleton was built from
                   (outline sinks sit at height 0)
    distance    -- offset distance in the skeleton's time units

    Returns a list of rings (lists of 2D points, clockwise like the input);
    empty when the offset is at or beyond the skeleton's max height.
    """
    if distance <= 0.0:
        raise ValueError("offset distance must be positive")
    base = {(round(float(x), 6), round(float(y), 6)) for x, y in base_points}

    # -- per-point heights: sources use their arc's height, sinks the min
    #    over the arcs containing them; outline points sit at height 0
    sink_h = {}
    for arc in skeleton:
        for s in arc.sinks:
            k = _pt_key(s)
            if k in base:
                sink_h[k] = 0.0
            else:
                sink_h[k] = min(sink_h.get(k, math.inf), arc.height)

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

    # -- per-face segments: a face crossed by the level set exactly twice
    #    contributes the segment between the two crossings; rings are the
    #    cycles of the resulting crossing graph (each crossing joins the
    #    two faces flanking its arc)
    by_face = defaultdict(list)
    for idx, (_pt, f0, f1) in enumerate(crossings):
        by_face[f0].append(idx)
        by_face[f1].append(idx)

    adj = defaultdict(set)
    for idxs in by_face.values():
        if len(idxs) != 2:
            continue  # face not crossed exactly once (degenerate at d)
        i, j = idxs
        pti, ptj = crossings[i][0], crossings[j][0]
        if (pti - ptj).length < 1e-9:
            continue  # zero-length segment at a coincident event point
        adj[i].add(j)
        adj[j].add(i)

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
