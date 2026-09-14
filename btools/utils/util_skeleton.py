"""Adapted from https://github.com/yonghah/polyskel"""

import hashlib
import heapq
import itertools as it
import math
import random
from collections import namedtuple

from mathutils import Vector


class Ray(namedtuple("Ray", "p v")):
    """A half-line: point ``p`` and direction ``v`` (parametric ``u >= 0``)."""

    __slots__ = ()


class Segment(namedtuple("Segment", "p v edge_id")):
    """A line segment from ``p`` to ``p + v`` (``0 <= u <= 1``).

    ``edge_id`` is the contour edge index: edge i ends at contour point i
    (holes continue the numbering). It keeps OriginalEdge and vertex edge
    references equality-consistent and lets consumers (offsets, roofs)
    refer back to source edges."""

    __slots__ = ()


def _cross(a, b):
    """2D scalar cross product."""
    return a.x * b.y - a.y * b.x


def _line_line_intersect(a, b):
    """Intersect two infinite lines given as ``(p, v)``.

    Returns ``(point, ua, ub)`` or ``None`` when the lines are parallel, where
    ``ua``/``ub`` are the parametric positions along ``a``/``b`` so callers can
    apply ray/segment ``u`` constraints themselves.
    """
    d = b.v.y * a.v.x - b.v.x * a.v.y
    if d == 0:
        return None

    dy = a.p.y - b.p.y
    dx = a.p.x - b.p.x
    ua = (b.v.x * dy - b.v.y * dx) / d
    ub = (a.v.x * dy - a.v.y * dx) / d

    return Vector((a.p.x + ua * a.v.x, a.p.y + ua * a.v.y)), ua, ub


def _intersect_lines(a, b):
    """Intersection point of two infinite lines, or None if parallel."""
    res = _line_line_intersect(a, b)
    return res[0] if res is not None else None


def _intersect_ray_line(ray, line):
    """Intersection of a ray and an infinite line, or None."""
    res = _line_line_intersect(ray, line)
    if res is None or res[1] < 0:
        return None
    return res[0]


def _intersect_rays(a, b):
    """Intersection point of two rays, or None."""
    res = _line_line_intersect(a, b)
    if res is None or res[1] < 0 or res[2] < 0:
        return None
    return res[0]


def _point_line_distance(pt, line):
    """Distance from ``pt`` to the infinite line ``(line.p, line.v)``."""
    return abs(_cross(line.v.normalized(), pt - line.p))


def _weighted_bisector(dir_left, dir_right, weight_left, weight_right):
    """Bisector direction of two wavefront edges with multiplicative
    weights (Biedl/Held/Huber/Kaaser/Palfrader; CGAL convention).

    weight w = tan(pitch): the edge's offset line moves inward at speed
    1/w and the wavefront vertex height equals its time. The vertex
    velocity v solves n_L . v = 1/w_L, n_R . v = 1/w_R over the unit
    inward normals (right-hand normals for clockwise contours).
    """
    nl = Vector((dir_left.y, -dir_left.x))
    nr = Vector((dir_right.y, -dir_right.x))
    det = nl.x * nr.y - nr.x * nl.y
    if det == 0:
        # parallel edges: the weighted bisector degenerates to the
        # angular one
        return -dir_left + dir_right
    pl = Vector((nl.y, -nl.x))
    pr = Vector((nr.y, -nr.x))
    return (pr / weight_left - pl / weight_right) / det


def window(lst):
    prevs, items, nexts = it.tee(lst, 3)
    prevs = it.islice(it.cycle(prevs), len(lst) - 1, None)
    nexts = it.islice(it.cycle(nexts), 1, None)
    return zip(prevs, items, nexts)


def approximately_equals(a, b):
    return a == b or ((a - b).length <= max(a.length, b.length) * 0.001)


def normalize_contour(contour):
    contour = [Vector((float(x), float(y))) for (x, y) in contour]
    return [
        point
        for prev, point, next in window(contour)
        if not (
            point == next or (point - prev).normalized() == (next - point).normalized()
        )
    ]


class SplitEvent(
    namedtuple("SplitEvent", "distance intersection_point etype vertex opposite_edge")
):
    __slots__ = ()

    def __str__(self):
        return f"{self.distance} Split event @ {self.intersection_point} from {self.vertex} to {self.opposite_edge}"


class EdgeEvent(
    namedtuple("EdgeEvent", "distance intersection_point etype vertex_a vertex_b")
):
    __slots__ = ()

    def __str__(self):
        return f"{self.distance} Edge event @ {self.intersection_point} between {self.vertex_a} and {self.vertex_b}"


OriginalEdge = namedtuple("OriginalEdge", "edge bisector_left, bisector_right")

Subtree = namedtuple("Subtree", "source, height, sinks, faces", defaults=((), ()))


class LAVertex:
    def __init__(
        self, point, edge_left, edge_right, direction_vectors=None, weights=None
    ):
        self.point = point
        self.edge_left = edge_left
        self.edge_right = edge_right
        self.prev = None
        self.next = None
        self.lav = None
        self._valid = True

        self._left_normalized = edge_left.v.normalized()
        self._right_normalized = edge_right.v.normalized()
        creator_vectors = (-self._left_normalized, self._right_normalized)
        if direction_vectors is None:
            direction_vectors = creator_vectors

        self._is_reflex = _cross(*direction_vectors) < 0
        self._w_left = weights[edge_left.edge_id] if weights is not None else 1.0
        self._w_right = weights[edge_right.edge_id] if weights is not None else 1.0

        if weights is None:
            bisector_v = creator_vectors[0] + creator_vectors[1]
        else:
            bisector_v = _weighted_bisector(
                self._left_normalized,
                self._right_normalized,
                self._w_left,
                self._w_right,
            )
            # -- keep the weighted direction oriented like the angular one,
            #    so the reflex flip below stays meaningful
            if bisector_v.dot(creator_vectors[0] + creator_vectors[1]) < 0:
                bisector_v = -bisector_v
        self._bisector = Ray(
            self.point.copy(),
            bisector_v * (-1 if self.is_reflex else 1),
        )

    @property
    def bisector(self):
        return self._bisector

    @property
    def is_reflex(self):
        return self._is_reflex

    @property
    def original_edges(self):
        return self.lav._slav._original_edges

    @property
    def slav_weights(self):
        return self.lav._slav._weights if self.lav is not None else None

    def next_event(self):
        events = []
        if self.is_reflex:
            for edge in self.original_edges:
                if edge.edge == self.edge_left or edge.edge == self.edge_right:
                    continue

                leftdot = abs(self._left_normalized.dot(edge.edge.v.normalized()))
                rightdot = abs(self._right_normalized.dot(edge.edge.v.normalized()))
                selfedge = self.edge_left if leftdot < rightdot else self.edge_right

                i = _intersect_lines(selfedge, edge.edge)
                if i is not None and not approximately_equals(i, self.point):
                    linvec = (self.point - i).normalized()
                    edvec = edge.edge.v.normalized()
                    if linvec.dot(edvec) < 0:
                        edvec = -edvec

                    bisecvec = edvec + linvec
                    if bisecvec.length == 0:
                        continue
                    bisector = Ray(i, bisecvec)
                    b = _intersect_ray_line(self.bisector, bisector)

                    if b is None:
                        continue

                    xleft = (
                        _cross(
                            edge.bisector_left.v.normalized(),
                            (b - edge.bisector_left.p).normalized(),
                        )
                        > 0
                    )
                    xright = (
                        _cross(
                            edge.bisector_right.v.normalized(),
                            (b - edge.bisector_right.p).normalized(),
                        )
                        < 0
                    )
                    xedge = (
                        _cross(edge.edge.v.normalized(), (b - edge.edge.p).normalized())
                        < 0
                    )

                    if not (xleft and xright and xedge):
                        continue

                    weights = self.slav_weights
                    w_opp = weights[edge.edge.edge_id] if weights is not None else 1.0
                    events.append(
                        SplitEvent(
                            w_opp * _point_line_distance(b, edge.edge),
                            b,
                            0,
                            self,
                            edge.edge,
                        )
                    )

        i_prev = _intersect_rays(self.bisector, self.prev.bisector)
        i_next = _intersect_rays(self.bisector, self.next.bisector)

        if i_prev is not None:
            events.append(
                EdgeEvent(
                    self._w_left * _point_line_distance(i_prev, self.edge_left),
                    i_prev,
                    1,
                    self.prev,
                    self,
                )
            )
        if i_next is not None:
            events.append(
                EdgeEvent(
                    self._w_right * _point_line_distance(i_next, self.edge_right),
                    i_next,
                    1,
                    self,
                    self.next,
                )
            )

        if not events:
            return None

        ev = min(
            events, key=lambda event: (self.point - event.intersection_point).length
        )

        return ev

    def invalidate(self):
        if self.lav is not None:
            self.lav.invalidate(self)
        else:
            self._valid = False

    @property
    def is_valid(self):
        return self._valid

    def __str__(self):
        return f"Vertex ({self.point.x:.2f};{self.point.y:.2f})"

    def __lt__(self, other):
        if isinstance(other, LAVertex):
            return self.point.x < other.point.x

    def __repr__(self):
        return "Vertex ({}) ({:.2f};{:.2f}), bisector {}, edges {} {}".format(
            "reflex" if self.is_reflex else "convex",
            self.point.x,
            self.point.y,
            self.bisector,
            self.edge_left,
            self.edge_right,
        )


class SLAV:
    def __init__(self, polygon, holes, weights=None):
        contours = [normalize_contour(polygon)]
        contours.extend([normalize_contour(hole) for hole in holes])

        # -- per-edge multiplicative weights (CGAL convention: w = tan of
        #    pitch; inset speed 1/w; vertex height = time), indexed by
        #    edge id. None keeps the classic unweighted path.
        self._weights = list(weights) if weights is not None else None

        self._lavs = []
        next_edge_id = 0
        for contour in contours:
            self._lavs.append(LAV.from_polygon(contour, self, next_edge_id))
            next_edge_id += len(contour)

        # store original polygon edges for calculating split events.
        # vertex.edge_left IS the edge ending at vertex.point, so reusing it
        # keeps OriginalEdge and vertex references equal (incl. edge_id)
        self._original_edges = [
            OriginalEdge(
                vertex.edge_left,
                vertex.prev.bisector,
                vertex.bisector,
            )
            for vertex in it.chain.from_iterable(self._lavs)
        ]

        # original polygon vertices, used by the zero-gradient gable pass
        self._original_points = {
            (p.x, p.y)
            for edge in self._original_edges
            for p in (edge.edge.p, edge.edge.p + edge.edge.v)
        }

    def __iter__(self):
        for lav in self._lavs:
            yield lav

    def __len__(self):
        return len(self._lavs)

    def empty(self):
        return len(self._lavs) == 0

    def handle_edge_event(self, event, zero_gradient):
        sinks = []
        # -- every arc source->sink is the death trace of the sink's
        #    wavefront vertex, flanked by that vertex's two edge faces
        arc_faces = []
        events = []

        lav = event.vertex_a.lav
        if event.vertex_a.prev == event.vertex_b.next:
            self._lavs.remove(lav)
            for vertex in list(lav):
                sinks.append(vertex.point)
                arc_faces.append((vertex.edge_left.edge_id, vertex.edge_right.edge_id))
                vertex.invalidate()
        else:
            new_vertex = lav.unify(
                event.vertex_a, event.vertex_b, event.intersection_point
            )
            if lav.head in (event.vertex_a, event.vertex_b):
                lav.head = new_vertex
            sinks.extend((event.vertex_a.point, event.vertex_b.point))
            arc_faces.append(
                (event.vertex_a.edge_left.edge_id, event.vertex_a.edge_right.edge_id)
            )
            arc_faces.append(
                (event.vertex_b.edge_left.edge_id, event.vertex_b.edge_right.edge_id)
            )
            next_event = new_vertex.next_event()
            if next_event is not None:
                events.append(next_event)

        # -- gable roof processing
        if zero_gradient:
            len_sinks = len(sinks)
            set_diff = {(s.x, s.y) for s in sinks} - self._original_points
            len_diff = len(set_diff)

            midpoint = event.intersection_point
            if len_sinks == 2 and len_diff == 0:
                midpoint = (sinks[0] + sinks[1]) / 2
            elif len_sinks == 3 and len_diff == 1:
                not_original = set_diff.pop()
                new_sinks = list(sinks)
                for idx, s in enumerate(new_sinks):
                    if (s.x, s.y) == not_original:
                        del new_sinks[idx]
                        break
                midpoint = (new_sinks[0] + new_sinks[1]) / 2

            event.intersection_point.x = midpoint.x
            event.intersection_point.y = midpoint.y

        return (
            Subtree(event.intersection_point, event.distance, sinks, arc_faces),
            events,
        )

    def handle_split_event(self, event):
        lav = event.vertex.lav

        sinks = [event.vertex.point]
        arc_faces = [(event.vertex.edge_left.edge_id, event.vertex.edge_right.edge_id)]
        vertices = []
        x = None  # right vertex
        y = None  # left vertex
        norm = event.opposite_edge.v.normalized()
        for v in it.chain.from_iterable(self._lavs):
            if norm == v._left_normalized and event.opposite_edge.p == v.edge_left.p:
                x = v
                y = x.prev
            elif (
                norm == v._right_normalized and event.opposite_edge.p == v.edge_right.p
            ):
                y = v
                x = y.next

            if x:
                xleft = (
                    _cross(
                        y.bisector.v.normalized(),
                        (event.intersection_point - y.point).normalized(),
                    )
                    >= 0
                )
                xright = (
                    _cross(
                        x.bisector.v.normalized(),
                        (event.intersection_point - x.point).normalized(),
                    )
                    <= 0
                )

                if xleft and xright:
                    break
                else:
                    x = None
                    y = None

        if x is None:
            return (None, [])

        v1 = LAVertex(
            event.intersection_point,
            event.vertex.edge_left,
            event.opposite_edge,
            weights=self._weights,
        )
        v2 = LAVertex(
            event.intersection_point,
            event.opposite_edge,
            event.vertex.edge_right,
            weights=self._weights,
        )

        v1.prev = event.vertex.prev
        v1.next = x
        event.vertex.prev.next = v1
        x.prev = v1

        v2.prev = y
        v2.next = event.vertex.next
        event.vertex.next.prev = v2
        y.next = v2

        new_lavs = None
        self._lavs.remove(lav)
        if lav != x.lav:
            # the split event actually merges two lavs
            self._lavs.remove(x.lav)
            new_lavs = [LAV.from_chain(v1, self)]
        else:
            new_lavs = [LAV.from_chain(v1, self), LAV.from_chain(v2, self)]

        for l in new_lavs:
            if len(l) > 2:
                self._lavs.append(l)
                vertices.append(l.head)
            else:
                # -- a collapsed 2-vertex LAV: BOTH vertices die here, so
                #    both edge pairs must be recorded for face coverage
                for sink_vertex in (l.head, l.head.next):
                    sinks.append(sink_vertex.point)
                    arc_faces.append(
                        (sink_vertex.edge_left.edge_id, sink_vertex.edge_right.edge_id)
                    )
                for v in list(l):
                    v.invalidate()

        events = []
        for vertex in vertices:
            next_event = vertex.next_event()
            if next_event is not None:
                events.append(next_event)

        event.vertex.invalidate()
        return (
            Subtree(event.intersection_point, event.distance, sinks, arc_faces),
            events,
        )


class LAV:
    def __init__(self, slav):
        self.head = None
        self._slav = slav
        self._len = 0

    @classmethod
    def from_polygon(cls, polygon, slav, start_edge_id=0):
        lav = cls(slav)
        n = len(polygon)
        for i, (prev, point, next) in enumerate(window(polygon)):
            lav._len += 1
            # -- edge i ends at contour point i; the wrap edge (from the
            #    last point back to the first) is edge 0
            vertex = LAVertex(
                point,
                Segment(prev, point - prev, start_edge_id + i),
                Segment(point, next - point, start_edge_id + (i + 1) % n),
                weights=slav._weights,
            )
            vertex.lav = lav
            if lav.head is None:
                lav.head = vertex
                vertex.prev = vertex.next = vertex
            else:
                vertex.next = lav.head
                vertex.prev = lav.head.prev
                vertex.prev.next = vertex
                lav.head.prev = vertex
        return lav

    @classmethod
    def from_chain(cls, head, slav):
        lav = cls(slav)
        lav.head = head
        for vertex in lav:
            lav._len += 1
            vertex.lav = lav
        return lav

    def invalidate(self, vertex):
        assert vertex.lav is self, "Tried to invalidate a vertex that's not mine"
        vertex._valid = False
        if self.head == vertex:
            self.head = self.head.next
        vertex.lav = None

    def unify(self, vertex_a, vertex_b, point):
        replacement = LAVertex(
            point,
            vertex_a.edge_left,
            vertex_b.edge_right,
            (vertex_b.bisector.v.normalized(), vertex_a.bisector.v.normalized()),
            weights=self._slav._weights,
        )
        replacement.lav = self

        if self.head in [vertex_a, vertex_b]:
            self.head = replacement

        vertex_a.prev.next = replacement
        vertex_b.next.prev = replacement
        replacement.prev = vertex_a.prev
        replacement.next = vertex_b.next

        vertex_a.invalidate()
        vertex_b.invalidate()

        self._len -= 1
        return replacement

    def __str__(self):
        return f"LAV {id(self)}"

    def __repr__(self):
        return f"{self!s} = {[vertex for vertex in self]}"

    def __len__(self):
        return self._len

    def __iter__(self):
        cur = self.head
        while True:
            yield cur
            cur = cur.next
            if cur == self.head:
                return

    def _show(self):
        cur = self.head
        while True:
            print(cur.__repr__())
            cur = cur.next
            if cur == self.head:
                break


class EventQueue:
    def __init__(self):
        self._data = []
        self._counter = it.count()

    def put(self, item):
        if item is not None:
            heapq.heappush(self._data, (item.distance, next(self._counter), item))

    def put_all(self, iterable):
        for item in iterable:
            self.put(item)

    def get(self):
        return heapq.heappop(self._data)[2]

    def empty(self):
        return len(self._data) == 0

    def peek(self):
        return self._data[0][2]

    def show(self):
        for item in self._data:
            print(item[2])


def _point_in_polygon(p, contour):
    """Ray-cast containment (winding independent)."""
    x, y = p.x, p.y
    inside = False
    n = len(contour)
    for i in range(n):
        x0, y0 = contour[i - 1]
        x1, y1 = contour[i]
        if (y0 > y) != (y1 > y):
            xint = x0 + (y - y0) * (x1 - x0) / (y1 - y0)
            if x < xint:
                inside = not inside
    return inside


def _dist_to_contour(p, contour):
    """Distance from p to the nearest contour SEGMENT."""
    best = math.inf
    n = len(contour)
    for i in range(n):
        x0, y0 = contour[i - 1]
        x1, y1 = contour[i]
        dx, dy = x1 - x0, y1 - y0
        seg2 = dx * dx + dy * dy
        if seg2 == 0.0:
            best = min(best, math.hypot(p.x - x0, p.y - y0))
        else:
            t = max(0.0, min(1.0, ((p.x - x0) * dx + (p.y - y0) * dy) / seg2))
            best = min(best, math.hypot(p.x - (x0 + t * dx), p.y - (y0 + t * dy)))
    return best


def _lav_vertices(lav, cap):
    """Bounded, de-duplicated vertex iteration: split-event surgery can
    leave linked lists that never return to head, which would spin
    forever; a healthy LAV never exceeds the input vertex count."""
    out = []
    seen = set()
    cur = lav.head
    if cur is None:
        return out
    steps = 0
    while steps < cap:
        steps += 1
        if id(cur) not in seen:
            seen.add(id(cur))
            out.append(cur)
        cur = cur.next
        if cur is None or cur == lav.head:
            break
    return out


def _run_slav(polygon, holes, zero_gradient, weights):
    """Run the wavefront simulation; returns (subtrees, normalized contours)."""
    normalized = [normalize_contour(polygon)] + [normalize_contour(h) for h in holes]
    total_verts = max(4, sum(len(c) for c in normalized))

    slav = SLAV(polygon, holes, weights)
    output = []
    prioque = EventQueue()

    for lav in slav:
        for vertex in lav:
            v = vertex.next_event()
            prioque.put(v)

    # -- hard iteration bound: degenerate wavefronts can generate
    #    zero-progress event cycles forever; breaking out leaves the
    #    leftovers to the terminal drain below
    max_events = 2000 + 50 * total_verts * total_verts
    processed = 0
    while not (prioque.empty() or slav.empty()):
        if processed > max_events:
            break
        processed += 1
        i = prioque.get()
        if isinstance(i, EdgeEvent):
            if not i.vertex_a.is_valid or not i.vertex_b.is_valid:
                continue
            arc, events = slav.handle_edge_event(i, zero_gradient)

        elif isinstance(i, SplitEvent):
            if not i.vertex.is_valid:
                continue
            arc, events = slav.handle_split_event(i)

        prioque.put_all(events)

        if arc is not None:
            output.append(arc)

    # -- terminal drain (item 5 follow-up): vertices still alive when the
    #    queue emptied belong to no-event chains the Felkel event set
    #    cannot represent -- apse chains (bisectors fanning at a common
    #    center) and diverging-bisector reflex chains. Close them
    #    geometrically: pairwise intersections of their bisectors give
    #    candidate meeting points; the one with the deepest clearance
    #    over the contour edge lines becomes the synthetic collapse source
    #    (unweighted runs only -- weighted times are not distances).
    if weights is None:
        leftovers = [
            v
            for lav in list(slav)
            for v in _lav_vertices(lav, total_verts + 8)
            if v.is_valid
        ]
        if len(leftovers) >= 2:
            lines = _edge_lines(normalized)

            def clearance(pt):
                # -- the collapse point must respect every contour edge
                #    (incl. holes), not just the leftovers' own faces
                return min(
                    abs((pt.x - x0) * dy - (pt.y - y0) * dx) for x0, y0, dx, dy in lines
                )

            candidates = []
            xs = [x for c in normalized for x, y in c]
            ys = [y for c in normalized for x, y in c]
            pad = max(max(xs) - min(xs), max(ys) - min(ys), 1.0)
            lo_x, hi_x = min(xs) - pad, max(xs) + pad
            lo_y, hi_y = min(ys) - pad, max(ys) + pad
            for a, b in it.combinations(leftovers, 2):
                res = _line_line_intersect(a.bisector, b.bisector)
                if res is not None:
                    p = res[0]
                    # -- near-parallel bisectors meet absurdly far out;
                    #    the collapse point is within the neighborhood
                    if lo_x <= p.x <= hi_x and lo_y <= p.y <= hi_y:
                        candidates.append(p)
            cx = sum(v.point.x for v in leftovers) / len(leftovers)
            cy = sum(v.point.y for v in leftovers) / len(leftovers)
            candidates.append(Vector((cx, cy)))

            # -- candidates must lie in the material region (or on the
            #    boundary -- apse centers sit on the discretized chain);
            #    far-out intersections of near-parallel bisectors and
            #    hole-interior points are invalid
            def candidate_ok(p):
                if any(_point_in_polygon(p, h) for h in normalized[1:]):
                    return False
                return (
                    _point_in_polygon(p, normalized[0])
                    or _dist_to_contour(p, normalized[0]) <= 1e-3
                )

            filtered = [p for p in candidates if candidate_ok(p)]
            if filtered:
                candidates = filtered

            source = max(candidates, key=clearance)
            height = clearance(source)
            sinks = [v.point for v in leftovers]
            arc_faces = [(v.edge_left.edge_id, v.edge_right.edge_id) for v in leftovers]
            output.append(Subtree(source, height, sinks, arc_faces))

            # -- a drained run is degenerate: per-LAV event arcs can carry
            #    times past the true contour meeting (events computed on
            #    one LAV ignore the other contour's wavefront). The drain
            #    height approximates the max inscribed radius; clamp event
            #    times to it (topology/meshing untouched) and drop sources
            #    sitting inside a hole outright
            if len(normalized) > 1:
                output = [
                    a
                    for a in output
                    if not any(_point_in_polygon(a.source, h) for h in normalized[1:])
                ]
            output = _cleanup_subtrees(output)
            output = [
                Subtree(a.source, min(a.height, height), a.sinks, a.faces)
                if a.height > height
                else a
                for a in output
            ]

    return output, normalized


def _edge_lines(normalized_contours):
    """[(p, v)] unit-direction edge lines in contour order."""
    lines = []
    for contour in normalized_contours:
        n = len(contour)
        for i in range(n):
            x0, y0 = contour[i - 1]
            x1, y1 = contour[i]
            dx, dy = x1 - x0, y1 - y0
            length = math.hypot(dx, dy) or 1.0
            lines.append((x0, y0, dx / length, dy / length))
    return lines


def _cleanup_subtrees(
    subtrees, normalized_contours=None, weights=None, ghost_filter=False
):
    """Drop degenerate artifacts from a skeleton run:

    - self arcs (source == sink within epsilon -- symmetric-tie artifact)
    - ghost arcs (unit weights only): a source's time must equal its
      perpendicular distance to the nearest contour edge line; arcs whose
      height is unreachable that way come from invalid tie sequences
    Returns the cleaned list (Subtree sinks/faces stay parallel)."""
    scale = 1.0
    lines = []
    if ghost_filter and normalized_contours and weights is None:
        lines = _edge_lines(normalized_contours)
        if lines:
            scale = max(max(abs(x0), abs(y0)) for x0, y0, _dx, _dy in lines) or 1.0
    tol = max(1e-3, 1e-4 * scale)

    cleaned = []
    for arc in subtrees:
        sinks, faces = [], []
        for s, f in zip(arc.sinks, arc.faces):
            if (s - arc.source).length <= 1e-4:
                continue  # self arc (symmetric-tie artifact)
            sinks.append(s)
            faces.append(f)
        if not sinks:
            continue
        if lines:
            nearest = min(
                abs(
                    (arc.source.y - y0) * dx - (arc.source.x - x0) * dy
                )  # cross product = perpendicular distance to the line
                for x0, y0, dx, dy in lines
            )
            if arc.height > nearest + tol:
                continue  # ghost arc: time unreachable from any edge line
        cleaned.append(Subtree(arc.source, arc.height, sinks, faces))
    return cleaned


def _skeleton_problems(subtrees, normalized_contours):
    """Consistency report for a skeleton run (roadmap item 5).

    Checks the contract the meshing and offsets rely on: every contour
    edge is covered by some arc's flanking faces, face ids are in range,
    and no arc has a non-positive height."""
    edge_count = sum(len(c) for c in normalized_contours)
    covered = set()
    problems = []
    for i, arc in enumerate(subtrees):
        if arc.height < -1e-9:
            problems.append("arc %d: non-positive height %.6g" % (i, arc.height))
        if not arc.sinks:
            problems.append("arc %d: no sinks" % i)
        for f in arc.faces:
            for e in f:
                if not 0 <= e < edge_count:
                    problems.append("arc %d: face id %r out of range" % (i, e))
                else:
                    covered.add(e)
    missing = sorted(set(range(edge_count)) - covered)
    if subtrees and missing:
        problems.append("edges not covered by any arc: %s" % missing[:8])
    if not subtrees and edge_count:
        problems.append("empty skeleton")
    return problems


def _jitter_contours(contours, seed, magnitude):
    """Deterministic micro-jitter that breaks exact-tie degeneracies.

    The Felkel/Obdrzalek simulation cannot represent simultaneous
    (multi-edge) events: symmetric inputs leave edges that never die.
    A hash-seeded uniform jitter of ~1e-6 splits the ties into a valid
    event sequence whose skeleton approximates the degenerate one far
    below the meshing tolerance."""
    rng = random.Random(seed)
    out = []
    for contour in contours:
        out.append(
            [
                (
                    x + rng.uniform(-magnitude, magnitude),
                    y + rng.uniform(-magnitude, magnitude),
                )
                for x, y in contour
            ]
        )
    return out


def _snap_to_base_points(subtrees, base_contours, tolerance=1e-3):
    """Replace output points that sit on (jittered) outline positions with
    the exact input points, so meshing/offsets keep their base linkage
    (tolerance matches utils.equal's default)."""
    base = [(x, y) for contour in base_contours for x, y in contour]

    def snap(pt):
        for x, y in base:
            if abs(pt.x - x) <= tolerance and abs(pt.y - y) <= tolerance:
                return Vector((x, y))
        return pt

    snapped = []
    for arc in subtrees:
        snapped.append(
            Subtree(
                snap(arc.source),
                arc.height,
                [snap(s) for s in arc.sinks],
                arc.faces,
            )
        )
    return snapped


def skeletonize(polygon, holes=None, zero_gradient=False, weights=None):
    """
    Compute the straight skeleton of a polygon.

    The polygon should be given as a list of vertices in counter-clockwise order.
    Holes is a list of the contours of the holes, the vertices of which should be in clockwise order.
    Zero gradient is an option to control the gradient between sinks and original_edges (produces gable roof)

    weights -- optional per-edge multiplicative weights (CGAL convention:
    w = tan of the roof pitch; the edge's offset line moves inward at
    speed 1/w and every wavefront vertex height equals its arrival time).
    Indexed by edge id: edge i ends at contour point i, holes continue
    the numbering. With weights, arc heights are already roof heights.

    Degenerate inputs (exact ties from symmetric footprints -- stars,
    apses, constant-thickness shapes) are retried on a deterministic
    micro-jittered copy of the contour; the result approximates the true
    skeleton far below the meshing tolerance.

    Returns the straight skeleton as a list of "subtrees", which are in the form of (source, height, sinks),
    where source is the highest points, height is its height, and sinks are the point connected to the source.
    """
    if holes is None:
        holes = []

    subtrees, normalized = _run_slav(polygon, holes, zero_gradient, weights)
    subtrees = _cleanup_subtrees(subtrees, normalized, weights)
    problems = _skeleton_problems(subtrees, normalized)

    attempts = 0
    while problems and attempts < 3:
        digest = hashlib.blake2b(
            repr([(round(x, 9), round(y, 9)) for c in normalized for x, y in c]).encode(
                "utf-8"
            ),
            digest_size=8,
        ).hexdigest()
        seed = "%s:%d" % (digest, attempts)
        # -- jitter ladder: start far below the meshing tolerance and
        #    escalate to break wider geometric ties
        magnitude = (1e-6 * 100**attempts) * max(
            1.0,
            max((max(x for x, _ in c) - min(x for x, _ in c)) for c in normalized),
        )
        jittered = _jitter_contours(normalized, seed, magnitude)
        re_subtrees, re_normalized = _run_slav(
            jittered[0], jittered[1:], zero_gradient, weights
        )
        re_subtrees = _cleanup_subtrees(
            re_subtrees, re_normalized, weights, ghost_filter=True
        )
        re_problems = _skeleton_problems(re_subtrees, re_normalized)
        if not re_problems:
            return _snap_to_base_points(re_subtrees, normalized)
        if len(re_problems) < len(problems):
            subtrees, problems = re_subtrees, re_problems
        attempts += 1

    return subtrees
