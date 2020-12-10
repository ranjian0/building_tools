""" Adapted from https://github.com/yonghah/polyskel
"""

import math
import heapq
import operator as op
import itertools as it

from enum import Enum
from collections import namedtuple


class Vector2:
    __slots__ = ["x", "y"]
    __hash__ = None

    def __init__(self, x=0, y=0):
        self.x = x
        self.y = y

    def __copy__(self):
        return self.__class__(self.x, self.y)

    copy = __copy__

    def __repr__(self):
        return "Vector2(%.2f, %.2f)" % (self.x, self.y)

    def __eq__(self, other):
        if isinstance(other, Vector2):
            return self.x == other.x and self.y == other.y
        else:
            assert hasattr(other, "__len__") and len(other) == 2
            return self.x == other[0] and self.y == other[1]

    def __ne__(self, other):
        return not self.__eq__(other)

    def __nonzero__(self):
        return bool(self.x != 0 or self.y != 0)

    def __len__(self):
        return 2

    def __getitem__(self, key):
        return (self.x, self.y)[key]

    def __setitem__(self, key, value):
        items = [self.x, self.y]
        items[key] = value
        self.x, self.y = items

    def __iter__(self):
        return iter((self.x, self.y))

    def __getattr__(self, name):
        try:
            return tuple([(self.x, self.y)["xy".index(c)] for c in name])
        except ValueError:
            raise AttributeError(name)

    def __add__(self, other):
        if isinstance(other, Vector2):
            # Vector + Vector -> Vector
            # Vector + Point -> Point
            # Point + Point -> Vector
            if self.__class__ is other.__class__:
                _class = Vector2
            else:
                _class = Point2
            return _class(self.x + other.x, self.y + other.y)
        else:
            assert hasattr(other, "__len__") and len(other) == 2
            return Vector2(self.x + other[0], self.y + other[1])

    __radd__ = __add__

    def __iadd__(self, other):
        if isinstance(other, Vector2):
            self.x += other.x
            self.y += other.y
        else:
            self.x += other[0]
            self.y += other[1]
        return self

    def __sub__(self, other):
        if isinstance(other, Vector2):
            if self.__class__ is other.__class__:
                _class = Vector2
            else:
                _class = Point2
            return _class(self.x - other.x, self.y - other.y)
        else:
            assert hasattr(other, "__len__") and len(other) == 2
            return Vector2(self.x - other[0], self.y - other[1])

    def __rsub__(self, other):
        if isinstance(other, Vector2):
            return Vector2(other.x - self.x, other.y - self.y)
        else:
            assert hasattr(other, "__len__") and len(other) == 2
            return Vector2(other.x - self[0], other.y - self[1])

    def __mul__(self, other):
        assert type(other) in (int, float)
        return Vector2(self.x * other, self.y * other)

    __rmul__ = __mul__

    def __imul__(self, other):
        assert type(other) in (int, float)
        self.x *= other
        self.y *= other
        return self

    def __div__(self, other):
        assert type(other) in (int, float)
        return Vector2(op.div(self.x, other), op.div(self.y, other))

    def __rdiv__(self, other):
        assert type(other) in (int, float)
        return Vector2(op.div(other, self.x), op.div(other, self.y))

    def __floordiv__(self, other):
        assert type(other) in (int, float)
        return Vector2(
            op.floordiv(self.x, other), op.floordiv(self.y, other)
        )

    def __rfloordiv__(self, other):
        assert type(other) in (int, float)
        return Vector2(
            op.floordiv(other, self.x), op.floordiv(other, self.y)
        )

    def __truediv__(self, other):
        assert type(other) in (int, float)
        return Vector2(op.truediv(self.x, other), op.truediv(self.y, other))

    def __rtruediv__(self, other):
        assert type(other) in (int, float)
        return Vector2(op.truediv(other, self.x), op.truediv(other, self.y))

    def __neg__(self):
        return Vector2(-self.x, -self.y)

    __pos__ = __copy__

    def __abs__(self):
        return math.sqrt(self.x ** 2 + self.y ** 2)

    magnitude = __abs__

    def magnitude_squared(self):
        return self.x ** 2 + self.y ** 2

    def normalize(self):
        d = self.magnitude()
        if d:
            self.x /= d
            self.y /= d
        return self

    def normalized(self):
        d = self.magnitude()
        if d:
            return Vector2(self.x / d, self.y / d)
        return self.copy()

    def dot(self, other):
        assert isinstance(other, Vector2)
        return self.x * other.x + self.y * other.y

    def cross(self):
        return Vector2(self.y, -self.x)

    def reflect(self, normal):
        # assume normal is normalized
        assert isinstance(normal, Vector2)
        d = 2 * (self.x * normal.x + self.y * normal.y)
        return Vector2(self.x - d * normal.x, self.y - d * normal.y)

    def angle(self, other):
        """Return the angle to the vector other"""
        return math.acos(self.dot(other) / (self.magnitude() * other.magnitude()))

    def project(self, other):
        """Return one vector projected on the vector other"""
        n = other.normalized()
        return self.dot(n) * n


class Geometry:
    def _connect_unimplemented(self, other):
        raise AttributeError(
            "Cannot connect %s to %s" % (self.__class__, other.__class__)
        )

    def _intersect_unimplemented(self, other):
        raise AttributeError(
            "Cannot intersect %s and %s" % (self.__class__, other.__class__)
        )

    _intersect_point2 = _intersect_unimplemented
    _intersect_line2 = _intersect_unimplemented
    _connect_point2 = _connect_unimplemented
    _connect_line2 = _connect_unimplemented

    def intersect(self, other):
        raise NotImplementedError

    def connect(self, other):
        raise NotImplementedError

    def distance(self, other):
        c = self.connect(other)
        if c:
            return c.length
        return 0.0


def _intersect_line2_line2(A, B):
    d = B.v.y * A.v.x - B.v.x * A.v.y
    if d == 0:
        return None

    dy = A.p.y - B.p.y
    dx = A.p.x - B.p.x
    ua = (B.v.x * dy - B.v.y * dx) / d
    if not A._u_in(ua):
        return None
    ub = (A.v.x * dy - A.v.y * dx) / d
    if not B._u_in(ub):
        return None

    return Point2(A.p.x + ua * A.v.x, A.p.y + ua * A.v.y)


def _connect_point2_line2(P, L):
    d = L.v.magnitude_squared()
    assert d != 0
    u = ((P.x - L.p.x) * L.v.x + (P.y - L.p.y) * L.v.y) / d
    if not L._u_in(u):
        u = max(min(u, 1.0), 0.0)
    return LineSegment2(P, Point2(L.p.x + u * L.v.x, L.p.y + u * L.v.y))


def _connect_line2_line2(A, B):
    d = B.v.y * A.v.x - B.v.x * A.v.y
    if d == 0:
        # Parallel, connect an endpoint with a line
        if isinstance(B, Ray2) or isinstance(B, LineSegment2):
            p1, p2 = _connect_point2_line2(B.p, A)
            return p2, p1
        # No endpoint (or endpoint is on A), possibly choose arbitrary point
        # on line.
        return _connect_point2_line2(A.p, B)

    dy = A.p.y - B.p.y
    dx = A.p.x - B.p.x
    ua = (B.v.x * dy - B.v.y * dx) / d
    if not A._u_in(ua):
        ua = max(min(ua, 1.0), 0.0)
    ub = (A.v.x * dy - A.v.y * dx) / d
    if not B._u_in(ub):
        ub = max(min(ub, 1.0), 0.0)

    return LineSegment2(
        Point2(A.p.x + ua * A.v.x, A.p.y + ua * A.v.y),
        Point2(B.p.x + ub * B.v.x, B.p.y + ub * B.v.y),
    )


class Point2(Vector2, Geometry):
    def __repr__(self):
        return "Point2(%.2f, %.2f)" % (self.x, self.y)

    def __lt__(self, other):
        if isinstance(other, Vector2):
            return self.x < other.x

    def __eq__(self, other):
        if isinstance(other, Vector2):
            return self.x == other.x and self.y == other.y

    def __hash__(self):
        return hash(repr(self))

    def intersect(self, other):
        return other._intersect_point2(self)

    def connect(self, other):
        return other._connect_point2(self)

    def _connect_point2(self, other):
        return LineSegment2(other, self)

    def _connect_line2(self, other):
        c = _connect_point2_line2(self, other)
        if c:
            return c._swap()


class Line2(Geometry):
    __slots__ = ["p", "v"]

    def __init__(self, *args):
        if len(args) == 3:
            assert (
                isinstance(args[0], Point2)
                and isinstance(args[1], Vector2)
                and type(args[2]) == float
            )
            self.p = args[0].copy()
            self.v = args[1] * args[2] / abs(args[1])
        elif len(args) == 2:
            if isinstance(args[0], Point2) and isinstance(args[1], Point2):
                self.p = args[0].copy()
                self.v = args[1] - args[0]
            elif isinstance(args[0], Point2) and isinstance(args[1], Vector2):
                self.p = args[0].copy()
                self.v = args[1].copy()
            else:
                raise AttributeError("%r" % (args,))
        elif len(args) == 1:
            if isinstance(args[0], Line2):
                self.p = args[0].p.copy()
                self.v = args[0].v.copy()
            else:
                raise AttributeError("%r" % (args,))
        else:
            raise AttributeError("%r" % (args,))

        if not self.v:
            raise AttributeError("Line has zero-length vector")

    def __copy__(self):
        return self.__class__(self.p, self.v)

    copy = __copy__

    def __repr__(self):
        return "Line2(<%.2f, %.2f> + u<%.2f, %.2f>)" % (
            self.p.x,
            self.p.y,
            self.v.x,
            self.v.y,
        )

    p1 = property(lambda self: self.p)
    p2 = property(lambda self: Point2(self.p.x + self.v.x, self.p.y + self.v.y))

    def _apply_transform(self, t):
        self.p = t * self.p
        self.v = t * self.v

    def _u_in(self, u):
        return True

    def intersect(self, other):
        return other._intersect_line2(self)

    def _intersect_line2(self, other):
        return _intersect_line2_line2(self, other)

    def connect(self, other):
        return other._connect_line2(self)

    def _connect_point2(self, other):
        return _connect_point2_line2(other, self)

    def _connect_line2(self, other):
        return _connect_line2_line2(other, self)


class Ray2(Line2):
    def __repr__(self):
        return "Ray2(<%.2f, %.2f> + u<%.2f, %.2f>)" % (
            self.p.x,
            self.p.y,
            self.v.x,
            self.v.y,
        )

    def _u_in(self, u):
        return u >= 0.0


class LineSegment2(Line2):
    def __repr__(self):
        return "LineSegment2(<%.2f, %.2f> to <%.2f, %.2f>)" % (
            self.p.x,
            self.p.y,
            self.p.x + self.v.x,
            self.p.y + self.v.y,
        )

    def _u_in(self, u):
        return u >= 0.0 and u <= 1.0

    def __abs__(self):
        return abs(self.v)

    def magnitude_squared(self):
        return self.v.magnitude_squared()

    def _swap(self):
        # used by connect methods to switch order of points
        self.p = self.p2
        self.v *= -1
        return self

    length = property(lambda self: abs(self.v))


def window(lst):
    prevs, items, nexts = it.tee(lst, 3)
    prevs = it.islice(it.cycle(prevs), len(lst) - 1, None)
    nexts = it.islice(it.cycle(nexts), 1, None)
    return zip(prevs, items, nexts)


def cross(a, b):
    res = a.x * b.y - b.x * a.y
    return res


def approximately_equals(a, b):
    return a == b or (abs(a - b) <= max(abs(a), abs(b)) * 0.001)


def approximately_same(point_a, point_b):
    return approximately_equals(point_a.x, point_b.x) and approximately_equals(
        point_a.y, point_b.y
    )


def normalize_contour(contour):
    contour = [Point2(float(x), float(y)) for (x, y) in contour]
    return [
        point
        for prev, point, next in window(contour)
        if not (
            point == next or (point - prev).normalized() == (next - point).normalized()
        )
    ]


# -- Event Type (etype) is 1
class SplitEvent(
    namedtuple("SplitEvent", "distance intersection_point etype vertex opposite_edge")
):
    __slots__ = ()

    def __str__(self):
        return "{} Split event @ {} from {} to {}".format(
            self.distance, self.intersection_point, self.vertex, self.opposite_edge
        )


# -- Event Type (etype) is 0
class EdgeEvent(
    namedtuple("EdgeEvent", "distance intersection_point etype vertex_a vertex_b")
):
    __slots__ = ()

    def __str__(self):
        return "{} Edge event @ {} between {} and {}".format(
            self.distance, self.intersection_point, self.vertex_a, self.vertex_b
        )


OriginalEdge = namedtuple("_OriginalEdge", "edge bisector_left, bisector_right")

Subtree = namedtuple("Subtree", "source, height, sinks")


class LAVertex:
    def __init__(self, point, edge_left, edge_right, direction_vectors=None):
        self.point = point
        self.edge_left = edge_left
        self.edge_right = edge_right
        self.prev = None
        self.next = None
        self.lav = None
        self._valid = True
        # this should be handled better. Maybe membership in lav implies validity?

        creator_vectors = (edge_left.v.normalized() * -1, edge_right.v.normalized())
        if direction_vectors is None:
            direction_vectors = creator_vectors

        self._is_reflex = (cross(*direction_vectors)) < 0
        self._bisector = Ray2(
            self.point, op.add(*creator_vectors) * (-1 if self.is_reflex else 1)
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

    def next_event(self):
        events = []
        if self.is_reflex:
            for edge in self.original_edges:
                if edge.edge == self.edge_left or edge.edge == self.edge_right:
                    continue

                leftdot = abs(
                    self.edge_left.v.normalized().dot(edge.edge.v.normalized())
                )
                rightdot = abs(
                    self.edge_right.v.normalized().dot(edge.edge.v.normalized())
                )
                selfedge = self.edge_left if leftdot < rightdot else self.edge_right

                i = Line2(selfedge).intersect(Line2(edge.edge))
                if i is not None and not approximately_equals(i, self.point):
                    # locate candidate b
                    linvec = (self.point - i).normalized()
                    edvec = edge.edge.v.normalized()
                    if linvec.dot(edvec) < 0:
                        edvec = -edvec

                    bisecvec = edvec + linvec
                    if abs(bisecvec) == 0:
                        continue
                    bisector = Line2(i, bisecvec)
                    b = bisector.intersect(self.bisector)

                    if b is None:
                        continue

                    xleft = (
                        cross(
                            edge.bisector_left.v.normalized(),
                            (b - edge.bisector_left.p).normalized(),
                        )
                        > 0
                    )
                    xright = (
                        cross(
                            edge.bisector_right.v.normalized(),
                            (b - edge.bisector_right.p).normalized(),
                        )
                        < 0
                    )
                    xedge = (
                        cross(edge.edge.v.normalized(), (b - edge.edge.p).normalized())
                        < 0
                    )

                    if not (xleft and xright and xedge):
                        continue

                    events.append(
                        SplitEvent(Line2(edge.edge).distance(b), b, 0, self, edge.edge)
                    )

        i_prev = self.bisector.intersect(self.prev.bisector)
        i_next = self.bisector.intersect(self.next.bisector)

        if i_prev is not None:
            events.append(
                EdgeEvent(
                    Line2(self.edge_left).distance(i_prev), i_prev, 1, self.prev, self
                )
            )
        if i_next is not None:
            events.append(
                EdgeEvent(
                    Line2(self.edge_right).distance(i_next), i_next, 1, self, self.next
                )
            )

        if not events:
            return None

        ev = min(
            events, key=lambda event: self.point.distance(event.intersection_point)
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
        return "Vertex ({:.2f};{:.2f})".format(self.point.x, self.point.y)

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
    def __init__(self, polygon, holes):
        contours = [normalize_contour(polygon)]
        contours.extend([normalize_contour(hole) for hole in holes])

        self._lavs = [LAV.from_polygon(contour, self) for contour in contours]

        # store original polygon edges for calculating split events
        self._original_edges = [
            OriginalEdge(
                LineSegment2(vertex.prev.point, vertex.point),
                vertex.prev.bisector,
                vertex.bisector,
            )
            for vertex in it.chain.from_iterable(self._lavs)
        ]

    def __iter__(self):
        for lav in self._lavs:
            yield lav

    def __len__(self):
        return len(self._lavs)

    def empty(self):
        return len(self._lavs) == 0

    def handle_edge_event(self, event, zero_gradient):
        sinks = []
        events = []

        lav = event.vertex_a.lav
        if event.vertex_a.prev == event.vertex_b.next:
            self._lavs.remove(lav)
            for vertex in list(lav):
                sinks.append(vertex.point)
                vertex.invalidate()
        else:
            new_vertex = lav.unify(
                event.vertex_a, event.vertex_b, event.intersection_point
            )
            if lav.head in (event.vertex_a, event.vertex_b):
                lav.head = new_vertex
            sinks.extend((event.vertex_a.point, event.vertex_b.point))
            next_event = new_vertex.next_event()
            if next_event is not None:
                events.append(next_event)

        # -- gable roof processing
        if zero_gradient:
            original_points = []
            for e in self._original_edges:
                original_points.extend([e.edge.p1, e.edge.p2])

            len_sinks = len(sinks)
            set_diff = set(sinks) - set(original_points)
            len_diff = len(list(set_diff))

            midpoint = event.intersection_point
            if len_sinks == 2 and len_diff == 0:
                midpoint = sum(sinks, (0, 0)) / 2
            elif len_sinks == 3 and len_diff == 1:
                new_sinks = [s for s in sinks]
                new_sinks.remove(set_diff.pop())
                midpoint = sum(new_sinks, (0, 0)) / 2

            event.intersection_point.x = midpoint.x
            event.intersection_point.y = midpoint.y

        return (Subtree(event.intersection_point, event.distance, sinks), events)

    def handle_split_event(self, event):
        lav = event.vertex.lav

        sinks = [event.vertex.point]
        vertices = []
        x = None  # right vertex
        y = None  # left vertex
        norm = event.opposite_edge.v.normalized()
        for v in it.chain.from_iterable(self._lavs):
            if (
                norm == v.edge_left.v.normalized()
                and event.opposite_edge.p == v.edge_left.p
            ):
                x = v
                y = x.prev
            elif (
                norm == v.edge_right.v.normalized()
                and event.opposite_edge.p == v.edge_right.p
            ):
                y = v
                x = y.next

            if x:
                xleft = (
                    cross(
                        y.bisector.v.normalized(),
                        (event.intersection_point - y.point).normalized(),
                    )
                    >= 0
                )
                xright = (
                    cross(
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
            event.intersection_point, event.vertex.edge_left, event.opposite_edge
        )
        v2 = LAVertex(
            event.intersection_point, event.opposite_edge, event.vertex.edge_right
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
                sinks.append(l.head.next.point)
                for v in list(l):
                    v.invalidate()

        events = []
        for vertex in vertices:
            next_event = vertex.next_event()
            if next_event is not None:
                events.append(next_event)

        event.vertex.invalidate()
        return (Subtree(event.intersection_point, event.distance, sinks), events)


class LAV:
    def __init__(self, slav):
        self.head = None
        self._slav = slav
        self._len = 0

    @classmethod
    def from_polygon(cls, polygon, slav):
        lav = cls(slav)
        for prev, point, next in window(polygon):
            lav._len += 1
            vertex = LAVertex(
                point, LineSegment2(prev, point), LineSegment2(point, next)
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
        return "LAV {}".format(id(self))

    def __repr__(self):
        return "{} = {}".format(str(self), [vertex for vertex in self])

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
        self.__data = []

    def put(self, item):
        if item is not None:
            heapq.heappush(self.__data, item)

    def put_all(self, iterable):
        for item in iterable:
            heapq.heappush(self.__data, item)

    def get(self):
        return heapq.heappop(self.__data)

    def empty(self):
        return len(self.__data) == 0

    def peek(self):
        return self.__data[0]

    def show(self):
        for item in self.__data:
            print(item)


def skeletonize(polygon, holes=None, zero_gradient=False):
    """
    Compute the straight skeleton of a polygon.

    The polygon should be given as a list of vertices in counter-clockwise order.
    Holes is a list of the contours of the holes, the vertices of which should be in clockwise order.
    Zero gradient is an option to control the gradient between sinks and original_edges (produces gable roof)

    Returns the straight skeleton as a list of "subtrees", which are in the form of (source, height, sinks),
    where source is the highest points, height is its height, and sinks are the point connected to the source.
    """
    slav = SLAV(polygon, holes)
    output = []
    prioque = EventQueue()

    for lav in slav:
        for vertex in lav:
            v = vertex.next_event()
            prioque.put(v)

    while not (prioque.empty() or slav.empty()):
        i = prioque.get()
        if isinstance(i, EdgeEvent):
            if not i.vertex_a.is_valid or not i.vertex_b.is_valid:
                continue
            (arc, events) = slav.handle_edge_event(i, zero_gradient)

        elif isinstance(i, SplitEvent):
            if not i.vertex.is_valid:
                continue
            (arc, events) = slav.handle_split_event(i)

        prioque.put_all(events)

        if arc is not None:
            output.append(arc)

    return output
