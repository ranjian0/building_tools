"""Room-layout utilities for interior generation (roadmap item 7).

Pure Python (no bpy): squarified treemaps (Bruls, Huizing & van Wijk
2000) for room subdivision, shared-edge adjacency for wall segments, and
spanning-tree door placement (minimum doors preserving reachability).
"""

import math
from collections import namedtuple

__all__ = [
    "Rect",
    "adjacency_segments",
    "offset_segment",
    "spanning_doors",
    "squarify",
]

Rect = namedtuple("Rect", "x y w h")


def _worst(row, length):
    """Worst (max) aspect ratio of a row of areas laid along ``length``."""
    if not row or length <= 0.0:
        return math.inf
    total = sum(row)
    thickness = total / length
    worst = 0.0
    for area in row:
        width = area / thickness if thickness > 0 else 0.0
        side = min(width, thickness)
        ratio = (max(width, thickness) / side) if side > 0 else math.inf
        worst = max(worst, ratio)
    return worst


def _layout_row(row, rect):
    """Place ``row`` areas in a strip spanning the shorter side."""
    thickness = sum(row) / min(rect.w, rect.h)
    out = []
    if rect.w < rect.h:
        # tall: strip spans the width; items side by side along x
        offset = rect.x
        for area in row:
            size = area / thickness
            out.append(Rect(offset, rect.y, size, thickness))
            offset += size
    else:
        # wide: strip spans the height; items stacked along y
        offset = rect.y
        for area in row:
            size = area / thickness
            out.append(Rect(rect.x, offset, thickness, size))
            offset += size
    return out


def _remainder(rect, row):
    """Rect left after laying ``row`` along the shorter side."""
    thickness = sum(row) / min(rect.w, rect.h)
    if rect.w < rect.h:
        return Rect(rect.x, rect.y + thickness, rect.w, rect.h - thickness)
    return Rect(rect.x + thickness, rect.y, rect.w - thickness, rect.h)


def _squarify(items, row, rect, out):
    if not items:
        out.extend(_layout_row(row, rect) if row else [])
        return
    nxt, rest = items[0], items[1:]
    length = min(rect.w, rect.h)
    if not row or _worst(row + [nxt], length) <= _worst(row, length):
        _squarify(rest, row + [nxt], rect, out)
    else:
        out.extend(_layout_row(row, rect))
        _squarify(items, [], _remainder(rect, row), out)


def squarify(rect, areas):
    """Squarified treemap: partition ``rect`` into room rects whose areas
    match ``areas`` (any positive weights; scaled to the rect's area).

    Returns ``list[Rect]`` in the same order as ``areas``."""
    total = float(sum(areas))
    if total <= 0.0 or rect.w <= 0.0 or rect.h <= 0.0 or not areas:
        return []
    scale = (rect.w * rect.h) / total
    # largest first (classic heuristic for better aspect ratios)
    order = sorted(range(len(areas)), key=lambda i: -areas[i])
    items = [areas[i] * scale for i in order]
    out = []
    _squarify(items, [], rect, out)
    # restore caller order
    by_pos = {pos: out[k] for k, pos in enumerate(order)}
    return [by_pos[i] for i in range(len(areas))]


def offset_segment(seg, amount):
    """Move a 2D segment perpendicular by ``amount``."""
    (x0, y0), (x1, y1) = seg
    dx, dy = x1 - x0, y1 - y0
    length = math.hypot(dx, dy)
    if length == 0.0:
        return seg
    nx, ny = -dy / length * amount, dx / length * amount
    return ((x0 + nx, y0 + ny), (x1 + nx, y1 + ny))


def adjacency_segments(rects, tol=1e-6):
    """Shared border segments between axis-aligned room rects.

    Returns ``[((i, j), (p0, p1)), ...]`` -- room indices and the 2D
    segment of their shared border (axis-aligned, world coords)."""
    segments = []
    n = len(rects)
    for i in range(n):
        for j in range(i + 1, n):
            a, b = rects[i], rects[j]
            # vertical shared border (same x span edge)
            for x in (a.x, a.x + a.w):
                if abs(x - b.x) < tol or abs(x - (b.x + b.w)) < tol:
                    lo = max(a.y, b.y)
                    hi = min(a.y + a.h, b.y + b.h)
                    if hi - lo > tol:
                        segments.append(((i, j), ((x, lo), (x, hi))))
            # horizontal shared border
            for y in (a.y, a.y + a.h):
                if abs(y - b.y) < tol or abs(y - (b.y + b.h)) < tol:
                    lo = max(a.x, b.x)
                    hi = min(a.x + a.w, b.x + b.w)
                    if hi - lo > tol:
                        segments.append(((i, j), ((lo, y), (hi, y))))
    return segments


def spanning_doors(segments, door_width, rng=None):
    """Minimum door set keeping all adjacent rooms connected.

    Builds the room adjacency graph from ``segments`` (adjacency_segments
    output), computes a spanning tree (maximum shared-border length
    first, so doors land on the room pairs that share the most wall),
    and places each door at the midpoint of its shared segment --
    jittered by ``rng`` (a random.Random) when provided.

    Returns ``[((i, j), (px, py)), ...]`` -- room pair and door center."""
    import heapq

    if not segments:
        return []
    rooms = {i for pair, _ in segments for i in pair}
    if len(rooms) < 2:
        return []

    # -- spanning tree over the adjacency graph, longest shared borders
    #    first (max-spanning via negated lengths on a min-heap)
    best = {}
    for pair, seg in segments:
        (x0, y0), (x1, y1) = seg
        length = math.hypot(x1 - x0, y1 - y0)
        key = frozenset(pair)
        if key not in best or length > best[key][0]:
            best[key] = (length, seg)

    edges = [
        (-length, min(pair), max(pair), seg) for pair, (length, seg) in best.items()
    ]
    heapq.heapify(edges)

    parent = {r: r for r in rooms}

    def find(r):
        while parent[r] != r:
            parent[r] = parent[parent[r]]
            r = parent[r]
        return r

    doors = []
    while edges:
        neg_len, i, j, seg = heapq.heappop(edges)
        ri, rj = find(i), find(j)
        if ri == rj:
            continue
        parent[ri] = rj
        (x0, y0), (x1, y1) = seg
        length = -neg_len
        if length < door_width:
            continue  # too narrow for a door; connectivity may suffer
        t = 0.5
        if rng is not None and length > door_width * 2.0:
            margin = (door_width / length) / 2.0
            t = rng.uniform(0.5 - (0.5 - margin), 0.5 + (0.5 - margin))
        px, py = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
        doors.append(((i, j), (px, py)))
    return doors
