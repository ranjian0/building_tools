
"""
Code is grabbed from Howard Trickey's Inset Polygon Addon

"""

import math
import random
from math import sqrt

# distances less than about DISTTOL will be considered
# essentially zero
DISTTOL = 1e-3
INVDISTTOL = 1e3


# ====================================================================================
#       GEOMETRY FUNCTIONS
# ====================================================================================

class Points(object):
    """Container of points without duplication, each mapped to an int.

    Points are either have dimension at least 2, maybe more.

    Implementation:
    In order to efficiently find duplicates, we quantize the points
    to triples of ints and map from quantized triples to vertex
    index.

    Attributes:
      pos: list of tuple of float - coordinates indexed by
          vertex number
      invmap: dict of (int, int, int) to int - quantized coordinates
          to vertex number map
    """

    def __init__(self, initlist=[]):
        self.pos = []
        self.invmap = dict()
        for p in initlist:
            self.AddPoint(p)

    @staticmethod
    def Quantize(p):
        """Quantize the float tuple into an int tuple.

        Args:
          p: tuple of float
        Returns:
          tuple of int - scaled by INVDISTTOL and rounded p
        """

        return tuple([int(round(v * INVDISTTOL)) for v in p])

    def AddPoint(self, p):
        """Add point p to the Points set and return vertex number.

        If there is an existing point which quantizes the same,,
        don't add a new one but instead return existing index.

        Args:
          p: tuple of float - coordinates (2-tuple or 3-tuple)
        Returns:
          int - the vertex number of added (or existing) point
        """

        qp = Points.Quantize(p)
        if qp in self.invmap:
            return self.invmap[qp]
        else:
            self.invmap[qp] = len(self.pos)
            self.pos.append(p)
            return len(self.pos) - 1

    def AddPoints(self, points):
        """Add another set of points to this set.

        We need to return a mapping from indices
        in the argument points space into indices
        in this point space.

        Args:
          points: Points - to union into this set
        Returns:
          list of int: maps added indices to new ones
        """

        vmap = [0] * len(points.pos)
        for i in range(len(points.pos)):
            vmap[i] = self.AddPoint(points.pos[i])
        return vmap

    def AddZCoord(self, z):
        """Change this in place to have a z coordinate, with value z.

        Assumes the coordinates are currently 2d.

        Args:
          z: the value of the z coordinate to add
        Side Effect:
          self now has a z-coordinate added
        """

        assert(len(self.pos) == 0 or len(self.pos[0]) == 2)
        newinvmap = dict()
        for i, (x, y) in enumerate(self.pos):
            newp = (x, y, z)
            self.pos[i] = newp
            newinvmap[self.Quantize(newp)] = i
        self.invmap = newinvmap

    def AddToZCoord(self, i, delta):
        """Change the z-coordinate of point with index i to add delta.

        Assumes the coordinates are currently 3d.

        Args:
          i: int - index of a point
          delta: float - value to add to z-coord
        """

        (x, y, z) = self.pos[i]
        self.pos[i] = (x, y, z + delta)


class PolyArea(object):
    """Contains a Polygonal Area (polygon with possible holes).

    A polygon is a list of vertex ids, each an index given by
    a Points object. The list represents a CCW-oriented
    outer boundary (implicitly closed).
    If there are holes, they are lists of CW-oriented vertices
    that should be contained in the outer boundary.
    (So the left face of both the poly and the holes is
    the filled part.)

    Attributes:
      points: Points
      poly: list of vertex ids
      holes: list of lists of vertex ids (each a hole in poly)
      data: any - application data (can hold color, e.g.)
    """

    def __init__(self, points=None, poly=None, holes=None, data=None):
        self.points = points if points else Points()
        self.poly = poly if poly else []
        self.holes = holes if holes else []
        self.data = data

    def AddHole(self, holepa):
        """Add a PolyArea's poly as a hole of self.

        Need to reverse the contour and
        adjust the the point indexes and self.points.

        Args:
          holepa: PolyArea
        """

        vmap = self.points.AddPoints(holepa.points)
        holepoly = [vmap[i] for i in holepa.poly]
        holepoly.reverse()
        self.holes.append(holepoly)

    def ContainsPoly(self, poly, points):
        """Tests if poly is contained within self.poly.

        Args:
          poly: list of int - indices into points
          points: Points - maps to coords
        Returns:
          bool - True if poly is fully contained within self.poly
        """

        for v in poly:
            if PointInside(points.pos[v], self.poly, self.points) == -1:
                return False
        return True

    def Normal(self):
        """Returns the normal of the polyarea's main poly."""

        pos = self.points.pos
        poly = self.poly
        if len(pos) == 0 or len(pos[0]) == 2 or len(poly) == 0:
            print("whoops, not enough info to calculate normal")
            return (0.0, 0.0, 1.0)
        return Newell(poly, self.points)


class PolyAreas(object):
    """Contains a list of PolyAreas and a shared Points.

    Attributes:
      polyareas: list of PolyArea
      points: Points
    """

    def __init__(self):
        self.polyareas = []
        self.points = Points()

    def scale_and_center(self, scaled_side_target):
        """Adjust the coordinates of the polyareas so that
        it is centered at the origin and has its longest
        dimension scaled to be scaled_side_target."""

        if len(self.points.pos) == 0:
            return
        (minv, maxv) = self.bounds()
        maxside = max([maxv[i] - minv[i] for i in range(2)])
        if maxside > 0.0:
            scale = scaled_side_target / maxside
        else:
            scale = 1.0
        translate = [-0.5 * (maxv[i] + minv[i]) for i in range(2)]
        dim = len(self.points.pos[0])
        if dim == 3:
            translate.append([0.0])
        for v in range(len(self.points.pos)):
            self.points.pos[v] = tuple([scale * (self.points.pos[v][i] +
                                                 translate[i]) for i in range(dim)])

    def bounds(self):
        """Find bounding box of polyareas in xy.

        Returns:
          ([minx,miny],[maxx,maxy]) - all floats
        """

        huge = 1e100
        minv = [huge, huge]
        maxv = [-huge, -huge]
        for pa in self.polyareas:
            for face in [pa.poly] + pa.holes:
                for v in face:
                    vcoords = self.points.pos[v]
                    for i in range(2):
                        if vcoords[i] < minv[i]:
                            minv[i] = vcoords[i]
                        if vcoords[i] > maxv[i]:
                            maxv[i] = vcoords[i]
        if minv[0] == huge:
            minv = [0.0, 0.0]
        if maxv[0] == huge:
            maxv = [0.0, 0.0]
        return (minv, maxv)


class Model(object):
    """Contains a generic 3d model.

    A generic 3d model has vertices with 3d coordinates.
    Each vertex gets a 'vertex id', which is an index that
    can be used to refer to the vertex and can be used
    to retrieve the 3d coordinates of the point.

    The actual visible part of the geometry are the faces,
    which are n-gons (n>2), specified by a vector of the
    n corner vertices.
    Faces may also have data associated with them,
    and the data will be copied into newly created faces
    from the most likely neighbor faces..

    Attributes:
      points: geom.Points - the 3d vertices
      faces: list of list of indices (each a CCW traversal of a face)
      face_data: list of any - if present, is parallel to
          faces list and holds arbitrary data
    """

    def __init__(self):
        self.points = Points()
        self.faces = []
        self.face_data = []


class Art(object):
    """Contains a vector art diagram.

    Attributes:
      paths: list of Path objects
    """

    def __init__(self):
        self.paths = []


class Paint(object):
    """A color or pattern to fill or stroke with.

    For now, just do colors, but could later do
    patterns or images too.

    Attributes:
      color: (r,g,b) triple of floats, 0.0=no color, 1.0=max color
    """

    def __init__(self, r=0.0, g=0.0, b=0.0):
        self.color = (r, g, b)

    @staticmethod
    def CMYK(c, m, y, k):
        """Return Paint specified in CMYK model.

        Uses formula from 6.2.4 of PDF Reference.

        Args:
          c, m, y, k: float - in range [0, 1]
        Returns:
          Paint - with components in rgb form now
        """

        return Paint(1.0 - min(1.0, c + k),
                     1.0 - min(1.0, m + k), 1.0 - min(1.0, y + k))

black_paint = Paint()
white_paint = Paint(1.0, 1.0, 1.0)

ColorDict = {
    'aqua': Paint(0.0, 1.0, 1.0),
    'black': Paint(0.0, 0.0, 0.0),
    'blue': Paint(0.0, 0.0, 1.0),
    'fuchsia': Paint(1.0, 0.0, 1.0),
    'gray': Paint(0.5, 0.5, 0.5),
    'green': Paint(0.0, 0.5, 0.0),
    'lime': Paint(0.0, 1.0, 0.0),
    'maroon': Paint(0.5, 0.0, 0.0),
    'navy': Paint(0.0, 0.0, 0.5),
    'olive': Paint(0.5, 0.5, 0.0),
    'purple': Paint(0.5, 0.0, 0.5),
    'red': Paint(1.0, 0.0, 0.0),
    'silver': Paint(0.75, 0.75, 0.75),
    'teal': Paint(0.0, 0.5, 0.5),
    'white': Paint(1.0, 1.0, 1.0),
    'yellow': Paint(1.0, 1.0, 0.0)
}


class Path(object):
    """Represents a path in the PDF sense, with painting instructions.

    Attributes:
      subpaths: list of Subpath objects
      filled: True if path is to be filled
      fillevenodd: True if use even-odd rule to fill (else non-zero winding)
      stroked: True if path is to be stroked
      fillpaint: Paint to fill with
      strokepaint: Paint to stroke with
    """

    def __init__(self):
        self.subpaths = []
        self.filled = False
        self.fillevenodd = False
        self.stroked = False
        self.fillpaint = black_paint
        self.strokepaint = black_paint

    def AddSubpath(self, subpath):
        """"Add a subpath."""

        self.subpaths.append(subpath)

    def Empty(self):
        """Returns True if this Path as no subpaths."""

        return not self.subpaths


class Subpath(object):
    """Represents a subpath in PDF sense, either open or closed.

    We'll represent lines, bezier pieces, circular arc pieces
    as tuples with letters giving segment type in first position
    and coordinates (2-tuples of floats) in the other positions.

    Segment types:
     ('L', a, b)       - line from a to b
     ('B', a, b, c, d) - cubic bezier from a to b, with control points c,d
     ('Q', a, b, c)    - quadratic bezier from a to b, with 1 control point c
     ('A', a, b, rad, xrot, large-arc, ccw) - elliptical arc from a to b,
       with rad=(rx, ry) as radii, xrot is x-axis rotation in degrees,
       large-arc is True if arc should be >= 180 degrees,
       ccw is True if start->end follows counter-clockwise direction
       (see SVG spec); note that after rad,
       the rest are floats or bools, not coordinate pairs
    Note that s[1] and s[2] are the start and end points for any segment s.

    Attributes:
      segments: list of segment tuples (see above)
      closed: True if closed
    """

    def __init__(self):
        self.segments = []
        self.closed = False

    def Empty(self):
        """Returns True if this subpath as no segments."""

        return not self.segments

    def AddSegment(self, seg):
        """Add a segment."""

        self.segments.append(seg)

    @staticmethod
    def SegStart(s):
        """Return start point for segment.

        Args:
          s: a segment tuple
        Returns:
          (float, float): the coordinates of the segment's start point
        """

        return s[1]

    @staticmethod
    def SegEnd(s):
        """Return end point for segment.

        Args:
          s: a segment tuple
        Returns:
          (float, float): the coordinates of the segment's end point
        """

        return s[2]


class TransformMatrix(object):
    """Transformation matrix for 2d coordinates.

    The transform matrix is:
      [ a b 0 ]
      [ c d 0 ]
      [ e f 1 ]
    and coordinate tranformation is defined by:
      [x' y' 1] = [x y 1] x TransformMatrix

    Attributes:
      a, b, c, d, e, f: floats
    """

    def __init__(self, a=1.0, b=0.0, c=0.0, d=1.0, e=0.0, f=0.0):
        self.a = a
        self.b = b
        self.c = c
        self.d = d
        self.e = e
        self.f = f

    def __str__(self):
        return str([self.a, self.b, self.c, self.d, self.e, self.f])

    def Copy(self):
        """Return a copy of this matrix."""

        return TransformMatrix(self.a, self.b, self.c, self.d, self.e, self.f)

    def ComposeTransform(self, a, b, c, d, e, f):
        """Apply the transform given the the arguments on top of this one.

        This is accomplished by returning t x sel
        where t is the transform matrix that would be formed from the args.

        Arguments:
          a, b, c, d, e, f: float - defines a composing TransformMatrix
        """

        newa = a * self.a + b * self.c
        newb = a * self.b + b * self.d
        newc = c * self.a + d * self.c
        newd = c * self.b + d * self.d
        newe = e * self.a + f * self.c + self.e
        newf = e * self.b + f * self.d + self.f
        self.a = newa
        self.b = newb
        self.c = newc
        self.d = newd
        self.e = newe
        self.f = newf

    def Apply(self, pt):
        """Return the result of applying this tranform to pt = (x,y).

        Arguments:
          (x, y) : (float, float)
        Returns:
          (x', y'): 2-tuple of floats, the result of [x y 1] x self
        """

        (x, y) = pt
        return (self.a * x + self.c * y + self.e,
                self.b * x + self.d * y + self.f)


def ApproxEqualPoints(p, q):
    """Return True if p and q are approximately the same points.

    Args:
      p: n-tuple of float
      q: n-tuple of float
    Returns:
      bool - True if the 1-norm <= DISTTOL
    """

    for i in range(len(p)):
        if abs(p[i] - q[i]) > DISTTOL:
            return False
        return True


def PointInside(v, a, points):
    """Return 1, 0, or -1 as v is inside, on, or outside polygon.

    Cf. Eric Haines ptinpoly in Graphics Gems IV.

    Args:
      v : (float, float) or (float, float, float) - coordinates of a point
      a : list of vertex indices defining polygon (assumed CCW)
      points: Points - to get coordinates for polygon
    Returns:
      1, 0, -1: as v is inside, on, or outside polygon a
    """

    (xv, yv) = (v[0], v[1])
    vlast = points.pos[a[-1]]
    (x0, y0) = (vlast[0], vlast[1])
    if x0 == xv and y0 == yv:
        return 0
    yflag0 = y0 > yv
    inside = False
    n = len(a)
    for i in range(0, n):
        vi = points.pos[a[i]]
        (x1, y1) = (vi[0], vi[1])
        if x1 == xv and y1 == yv:
            return 0
        yflag1 = y1 > yv
        if yflag0 != yflag1:
            xflag0 = x0 > xv
            xflag1 = x1 > xv
            if xflag0 == xflag1:
                if xflag0:
                    inside = not inside
            else:
                z = x1 - (y1 - yv) * (x0 - x1) / (y0 - y1)
                if z >= xv:
                    inside = not inside
        x0 = x1
        y0 = y1
        yflag0 = yflag1
    if inside:
        return 1
    else:
        return -1


def SignedArea(polygon, points):
    """Return the area of the polgon, positive if CCW, negative if CW.

    Args:
      polygon: list of vertex indices
      points: Points
    Returns:
      float - area of polygon, positive if it was CCW, else negative
    """

    a = 0.0
    n = len(polygon)
    for i in range(0, n):
        u = points.pos[polygon[i]]
        v = points.pos[polygon[(i + 1) % n]]
        a += u[0] * v[1] - u[1] * v[0]
    return 0.5 * a


def VecAdd(a, b):
    """Return vector a-b.

    Args:
      a: n-tuple of floats
      b: n-tuple of floats
    Returns:
      n-tuple of floats - pairwise addition a+b
    """

    n = len(a)
    assert(n == len(b))
    return tuple([a[i] + b[i] for i in range(n)])


def VecSub(a, b):
    """Return vector a-b.

    Args:
      a: n-tuple of floats
      b: n-tuple of floats
    Returns:
      n-tuple of floats - pairwise subtraction a-b
    """

    n = len(a)
    assert(n == len(b))
    return tuple([a[i] - b[i] for i in range(n)])


def VecDot(a, b):
    """Return the dot product of two vectors.

    Args:
      a: n-tuple of floats
      b: n-tuple of floats
    Returns:
      n-tuple of floats - dot product of a and b
    """

    n = len(a)
    assert(n == len(b))
    sum = 0.0
    for i in range(n):
        sum += a[i] * b[i]
    return sum


def VecLen(a):
    """Return the Euclidean length of the argument vector.

    Args:
      a: n-tuple of floats
    Returns:
      float: the 2-norm of a
    """

    s = 0.0
    for v in a:
        s += v * v
    return math.sqrt(s)


def Newell(poly, points):
    """Use Newell method to find polygon normal.

    Assume poly has length at least 3 and points are 3d.

    Args:
      poly: list of int - indices into points.pos
      points: Points - assumed 3d
    Returns:
      (float, float, float) - the average normal
    """

    sumx = 0.0
    sumy = 0.0
    sumz = 0.0
    n = len(poly)
    pos = points.pos
    for i, ai in enumerate(poly):
        bi = poly[(i + 1) % n]
        a = pos[ai]
        b = pos[bi]
        sumx += (a[1] - b[1]) * (a[2] + b[2])
        sumy += (a[2] - b[2]) * (a[0] + b[0])
        sumz += (a[0] - b[0]) * (a[1] + b[1])
    return Norm3(sumx, sumy, sumz)


def Norm3(x, y, z):
    """Return vector (x,y,z) normalized by dividing by squared length.
    Return (0.0, 0.0, 1.0) if the result is undefined."""
    sqrlen = x * x + y * y + z * z
    if sqrlen < 1e-100:
        return (0.0, 0.0, 1.0)
    else:
        try:
            d = math.sqrt(sqrlen)
            return (x / d, y / d, z / d)
        except:
            return (0.0, 0.0, 1.0)


# We're using right-hand coord system, where
# forefinger=x, middle=y, thumb=z on right hand.
# Then, e.g., (1,0,0) x (0,1,0) = (0,0,1)
def Cross3(a, b):
    """Return the cross product of two vectors, a x b."""

    (ax, ay, az) = a
    (bx, by, bz) = b
    return (ay * bz - az * by, az * bx - ax * bz, ax * by - ay * bx)


def MulPoint3(p, m):
    """Return matrix multiplication of p times m
    where m is a 4x3 matrix and p is a 3d point, extended with 1."""

    (x, y, z) = p
    return (x * m[0] + y * m[3] + z * m[6] + m[9],
            x * m[1] + y * m[4] + z * m[7] + m[10],
            x * m[2] + y * m[5] + z * m[8] + m[11])


# ====================================================================================
#       TRIQUAD FUNCTIONS
# ====================================================================================

# Points are 3-tuples or 2-tuples of reals: (x,y,z) or (x,y)
# Faces are lists of integers (vertex indices into coord lists)
# After triangulation/quadrangulation, the tris and quads will
# be tuples instead of lists.
# Vmaps are lists taking vertex index -> Point

TOL = 1e-7     # a tolerance for fuzzy equality
GTHRESH = 75   # threshold above which use greedy to _Quandrangulate
ANGFAC = 1.0   # weighting for angles in quad goodness measure
DEGFAC = 10.0  # weighting for degree in quad goodness measure

# Angle kind constants
Ang0 = 1
Angconvex = 2
Angreflex = 3
Angtangential = 4
Ang360 = 5


def TriangulateFace(face, points):
    """Triangulate the given face.

    Uses an easy triangulation first, followed by a constrained delauney
    triangulation to get better shaped triangles.

    Args:
      face: list of int - indices in points, assumed CCW-oriented
      points: geom.Points - holds coordinates for vertices
    Returns:
      list of (int, int, int) - 3-tuples are CCW-oriented vertices of
          triangles making up the triangulation
    """

    if len(face) <= 3:
        return [tuple(face)]
    tris = EarChopTriFace(face, points)
    bord = _BorderEdges([face])
    triscdt = _CDT(tris, bord, points)
    return triscdt


def TriangulateFaceWithHoles(face, holes, points):
    """Like TriangulateFace, but with holes inside the face.

    Works by making one complex polygon that has segments to
    and from the holes ("islands"), and then using the same method
    as TriangulateFace.

    Args:
      face: list of int - indices in points, assumed CCW-oriented
      holes: list of list of int - each sublist is like face
          but CW-oriented and assumed to be inside face
      points: geom.Points - holds coordinates for vertices
    Returns:
      list of (int, int, int) - 3-tuples are CCW-oriented vertices of
          triangles making up the triangulation
    """

    if len(holes) == 0:
        return TriangulateFace(face, points)
    allfaces = [face] + holes
    sholes = [_SortFace(h, points) for h in holes]
    joinedface = _JoinIslands(face, sholes, points)
    tris = EarChopTriFace(joinedface, points)
    bord = _BorderEdges(allfaces)
    triscdt = _CDT(tris, bord, points)
    return triscdt


def QuadrangulateFace(face, points):
    """Quadrangulate the face (subdivide into convex quads and tris).

    Like TriangulateFace, but after triangulating, join as many pairs
    of triangles as possible into convex quadrilaterals.

    Args:
      face: list of int - indices in points, assumed CCW-oriented
      points: geom.Points - holds coordinates for vertices
    Returns:
      list of 3-tuples or 4-tuples of ints - CCW-oriented vertices of
          quadrilaterals and triangles making up the quadrangulation.
    """

    if len(face) <= 3:
        return [tuple(face)]
    tris = EarChopTriFace(face, points)
    bord = _BorderEdges([face])
    triscdt = _CDT(tris, bord, points)
    qs = _Quandrangulate(triscdt, bord, points)
    return qs


def QuadrangulateFaceWithHoles(face, holes, points):
    """Like QuadrangulateFace, but with holes inside the faces.

    Args:
      face: list of int - indices in points, assumed CCW-oriented
      holes: list of list of int - each sublist is like face
          but CW-oriented and assumed to be inside face
      points: geom.Points - holds coordinates for vertices
    Returns:
      list of 3-tuples or 4-tuples of ints - CCW-oriented vertices of
          quadrilaterals and triangles making up the quadrangulation.
    """

    if len(holes) == 0:
        return QuadrangulateFace(face, points)
    allfaces = [face] + holes
    sholes = [_SortFace(h, points) for h in holes]
    joinedface = _JoinIslands(face, sholes, points)
    tris = EarChopTriFace(joinedface, points)
    bord = _BorderEdges(allfaces)
    triscdt = _CDT(tris, bord, points)
    qs = _Quandrangulate(triscdt, bord, points)
    return qs


def _SortFace(face, points):
    """Rotate face so leftmost vertex is first, where face is
    list of indices in points."""

    n = len(face)
    if n <= 1:
        return face
    lefti = 0
    leftv = face[0]
    for i in range(1, n):
        # following comparison is lexicographic on n-tuple
        # so sorts on x first, using lower y as tie breaker.
        if points.pos[face[i]] < points.pos[leftv]:
            lefti = i
            leftv = face[i]
    return face[lefti:] + face[0:lefti]


def EarChopTriFace(face, points):
    """Triangulate given face, with coords given by indexing into points.
    Return list of faces, each of which will be a triangle.
    Use the ear-chopping method."""

    # start with lowest coord in 2d space to try
    # to get a pleasing uniform triangulation if starting with
    # a regular structure (like a grid)
    start = _GetLeastIndex(face, points)
    ans = []
    incr = 1
    n = len(face)
    while n > 3:
        i = _FindEar(face, n, start, incr, points)
        vm1 = face[(i - 1) % n]
        v0 = face[i]
        v1 = face[(i + 1) % n]
        face = _ChopEar(face, i)
        n = len(face)
        incr = - incr
        if incr == 1:
            start = i % n
        else:
            start = (i - 1) % n
        ans.append((vm1, v0, v1))
    ans.append(tuple(face))
    return ans


def _GetLeastIndex(face, points):
    """Return index of coordinate that is leftmost, lowest in face."""

    bestindex = 0
    bestpos = points.pos[face[0]]
    for i in range(1, len(face)):
        pos = points.pos[face[i]]
        if pos[0] < bestpos[0] or \
                (pos[0] == bestpos[0] and pos[1] < bestpos[1]):
            bestindex = i
            bestpos = pos
    return bestindex


def _FindEar(face, n, start, incr, points):
    """An ear of a polygon consists of three consecutive vertices
    v(-1), v0, v1 such that v(-1) can connect to v1 without intersecting
    the polygon.
    Finds an ear, starting at index 'start' and moving
    in direction incr. (We attempt to alternate directions, to find
    'nice' triangulations for simple convex polygons.)
    Returns index into faces of v0 (will always find one, because
    uses a desperation mode if fails to find one with above rule)."""

    angk = _ClassifyAngles(face, n, points)
    for mode in range(0, 5):
        i = start
        while True:
            if _IsEar(face, i, n, angk, points, mode):
                return i
            i = (i + incr) % n
            if i == start:
                break  # try next higher desperation mode


def _IsEar(face, i, n, angk, points, mode):
    """Return true, false depending on ear status of vertices
    with indices i-1, i, i+1.
    mode is amount of desperation: 0 is Normal mode,
    mode 1 allows degenerate triangles (with repeated vertices)
    mode 2 allows local self crossing (folded) ears
    mode 3 allows any convex vertex (should always be one)
    mode 4 allows anything (just to be sure loop terminates!)"""

    k = angk[i]
    vm2 = face[(i - 2) % n]
    vm1 = face[(i - 1) % n]
    v0 = face[i]
    v1 = face[(i + 1) % n]
    v2 = face[(i + 2) % n]
    if vm1 == v0 or v0 == v1:
        return (mode > 0)
    b = (k == Angconvex or k == Angtangential or k == Ang0)
    c = _InCone(vm1, v0, v1, v2, angk[(i + 1) % n], points) and \
        _InCone(v1, vm2, vm1, v0, angk[(i - 1) % n], points)
    if b and c:
        return _EarCheck(face, n, angk, vm1, v0, v1, points)
    if mode < 2:
        return False
    if mode == 3:
        return SegsIntersect(vm2, vm1, v0, v1, points)
    if mode == 4:
        return b
    return True


def _EarCheck(face, n, angk, vm1, v0, v1, points):
    """Return True if the successive vertices vm1, v0, v1
    forms an ear.  We already know that it is not a reflex
    Angle, and that the local cone containment is ok.
    What remains to check is that the edge vm1-v1 doesn't
    intersect any other edge of the face (besides vm1-v0
    and v0-v1).  Equivalently, there can't be a reflex Angle
    inside the triangle vm1-v0-v1.  (Well, there are
    messy cases when other points of the face coincide with
    v0 or touch various lines involved in the ear.)"""
    for j in range(0, n):
        fv = face[j]
        k = angk[j]
        b = (k == Angreflex or k == Ang360) \
            and not(fv == vm1 or fv == v0 or fv == v1)
        if b:
            # Is fv inside closure of triangle (vm1,v0,v1)?
            c = not(Ccw(v0, vm1, fv, points)
                    or Ccw(vm1, v1, fv, points)
                    or Ccw(v1, v0, fv, points))
            fvm1 = face[(j - 1) % n]
            fv1 = face[(j + 1) % n]
            # To try to deal with some degenerate cases,
            # also check to see if either segment attached to fv
            # intersects either segment of potential ear.
            d = SegsIntersect(fvm1, fv, vm1, v0, points) or \
                SegsIntersect(fvm1, fv, v0, v1, points) or \
                SegsIntersect(fv, fv1, vm1, v0, points) or \
                SegsIntersect(fv, fv1, v0, v1, points)
            if c or d:
                return False
    return True


def _ChopEar(face, i):
    """Return a copy of face (of length n), omitting element i."""

    return face[0:i] + face[i + 1:]


def _InCone(vtest, a, b, c, bkind, points):
    """Return true if point with index vtest is in Cone of points with
    indices a, b, c, where Angle ABC has AngleKind Bkind.
    The Cone is the set of points inside the left face defined by
    segments ab and bc, disregarding all other segments of polygon for
    purposes of inside test."""

    if bkind == Angreflex or bkind == Ang360:
        if _InCone(vtest, c, b, a, Angconvex, points):
            return False
        return not((not(Ccw(b, a, vtest, points))
                    and not(Ccw(b, vtest, a, points))
                    and Ccw(b, a, vtest, points))
                   or
                   (not(Ccw(b, c, vtest, points))
                    and not(Ccw(b, vtest, c, points))
                    and Ccw(b, a, vtest, points)))
    else:
        return Ccw(a, b, vtest, points) and Ccw(b, c, vtest, points)


def _JoinIslands(face, holes, points):
    """face is a CCW face containing the CW faces in the holes list,
    where each hole is sorted so the leftmost-lowest vertex is first.
    faces and holes are given as lists of indices into points.
    The holes should be sorted by softface.
    Add edges to make a new face that includes the holes (a Ccw traversal
    of the new face will have the inside always on the left),
    and return the new face."""

    while len(holes) > 0:
        (hole, holeindex) = _LeftMostFace(holes, points)
        holes = holes[0:holeindex] + holes[holeindex + 1:]
        face = _JoinIsland(face, hole, points)
    return face


def _JoinIsland(face, hole, points):
    """Return a modified version of face that splices in the
    vertices of hole (which should be sorted)."""

    if len(hole) == 0:
        return face
    hv0 = hole[0]
    d = _FindDiag(face, hv0, points)
    newface = face[0:d + 1] + hole + [hv0] + face[d:]
    return newface


def _LeftMostFace(holes, points):
    """Return (hole,index of hole in holes) where hole has
    the leftmost first vertex.  To be able to handle empty
    holes gracefully, call an empty hole 'leftmost'.
    Assumes holes are sorted by softface."""

    assert(len(holes) > 0)
    lefti = 0
    lefthole = holes[0]
    if len(lefthole) == 0:
        return (lefthole, lefti)
    leftv = lefthole[0]
    for i in range(1, len(holes)):
        ihole = holes[i]
        if len(ihole) == 0:
            return (ihole, i)
        iv = ihole[0]
        if points.pos[iv] < points.pos[leftv]:
            (lefti, lefthole, leftv) = (i, ihole, iv)
    return (lefthole, lefti)


def _FindDiag(face, hv, points):
    """Find a vertex in face that can see vertex hv, if possible,
    and return the index into face of that vertex.
    Should be able to find a diagonal that connects a vertex of face
    left of v to hv without crossing face, but try two
    more desperation passes after that to get SOME diagonal, even if
    it might cross some edge somewhere.
    First desperation pass (mode == 1): allow points right of hv.
    Second desperation pass (mode == 2): allow crossing boundary poly"""

    besti = - 1
    bestdist = 1e30
    for mode in range(0, 3):
        for i in range(0, len(face)):
            v = face[i]
            if mode == 0 and points.pos[v] > points.pos[hv]:
                continue  # in mode 0, only want points left of hv
            dist = _DistSq(v, hv, points)
            if dist < bestdist:
                if _IsDiag(i, v, hv, face, points) or mode == 2:
                    (besti, bestdist) = (i, dist)
        if besti >= 0:
            break  # found one, so don't need other modes
    assert(besti >= 0)
    return besti


def _IsDiag(i, v, hv, face, points):
    """Return True if vertex v (at index i in face) can see vertex hv.
    v and hv are indices into points.
    (v, hv) is a diagonal if hv is in the cone of the Angle at index i on face
    and no segment in face intersects (h, hv).
    """

    n = len(face)
    vm1 = face[(i - 1) % n]
    v1 = face[(i + 1) % n]
    k = _AngleKind(vm1, v, v1, points)
    if not _InCone(hv, vm1, v, v1, k, points):
        return False
    for j in range(0, n):
        vj = face[j]
        vj1 = face[(j + 1) % n]
        if SegsIntersect(v, hv, vj, vj1, points):
            return False
    return True


def _DistSq(a, b, points):
    """Return distance squared between coords with indices a and b in points.
    """

    diff = Sub2(points.pos[a], points.pos[b])
    return Dot2(diff, diff)


def _BorderEdges(facelist):
    """Return a set of (u,v) where u and v are successive vertex indices
    in some face in the list in facelist."""

    ans = set()
    for i in range(0, len(facelist)):
        f = facelist[i]
        for j in range(1, len(f)):
            ans.add((f[j - 1], f[j]))
        ans.add((f[-1], f[0]))
    return ans


def _CDT(tris, bord, points):
    """Tris is a list of triangles ((a,b,c), CCW-oriented indices into points)
    Bord is a set of border edges (u,v), oriented so that tris
    is a triangulation of the left face of the border(s).
    Make the triangulation "Constrained Delaunay" by flipping "reversed"
    quadrangulaterals until can flip no more.
    Return list of triangles in new triangulation."""

    td = _TriDict(tris)
    re = _ReveresedEdges(tris, td, bord, points)
    ts = set(tris)
    # reverse the reversed edges until done.
    # reversing and edge adds new edges, which may or
    # may not be reversed or border edges, to re for
    # consideration, but the process will stop eventually.
    while len(re) > 0:
        (a, b) = e = re.pop()
        if e in bord or not _IsReversed(e, td, points):
            continue
        # rotate e in quad adbc to get other diagonal
        erev = (b, a)
        tl = td.get(e)
        tr = td.get(erev)
        if not tl or not tr:
            continue  # shouldn't happen
        c = _OtherVert(tl, a, b)
        d = _OtherVert(tr, a, b)
        if c is None or d is None:
            continue  # shouldn't happen
        newt1 = (c, d, b)
        newt2 = (c, a, d)
        del td[e]
        del td[erev]
        td[(c, d)] = newt1
        td[(d, b)] = newt1
        td[(b, c)] = newt1
        td[(d, c)] = newt2
        td[(c, a)] = newt2
        td[(a, d)] = newt2
        if tl in ts:
            ts.remove(tl)
        if tr in ts:
            ts.remove(tr)
        ts.add(newt1)
        ts.add(newt2)
        re.extend([(d, b), (b, c), (c, a), (a, d)])
    return list(ts)


def _TriDict(tris):
    """tris is a list of triangles (a,b,c), CCW-oriented indices.
    Return dict mapping all edges in the triangles to the containing
    triangle list."""

    ans = dict()
    for i in range(0, len(tris)):
        (a, b, c) = t = tris[i]
        ans[(a, b)] = t
        ans[(b, c)] = t
        ans[(c, a)] = t
    return ans


def _ReveresedEdges(tris, td, bord, points):
    """Return list of reversed edges in tris.
    Only want edges not in bord, and only need one representative
    of (u,v)/(v,u), so choose the one with u < v.
    td is dictionary from _TriDict, and is used to find left and right
    triangles of edges."""

    ans = []
    for i in range(0, len(tris)):
        (a, b, c) = tris[i]
        for e in [(a, b), (b, c), (c, a)]:
            if e in bord:
                continue
            (u, v) = e
            if u < v:
                if _IsReversed(e, td, points):
                    ans.append(e)
    return ans


def _IsReversed(e, td, points):
    """If e=(a,b) is a non-border edge, with left-face triangle tl and
    right-face triangle tr, then it is 'reversed' if the circle through
    a, b, and (say) the other vertex of tl containts the other vertex of tr.
    td is a _TriDict, for finding triangles containing edges, and points
    gives the coordinates for vertex indices used in edges."""

    tl = td.get(e)
    if not tl:
        return False
    (a, b) = e
    tr = td.get((b, a))
    if not tr:
        return False
    c = _OtherVert(tl, a, b)
    d = _OtherVert(tr, a, b)
    if c is None or d is None:
        return False
    return InCircle(a, b, c, d, points)


def _OtherVert(tri, a, b):
    """tri should be a tuple of 3 vertex indices, two of which are a and b.
    Return the third index, or None if all vertices are a or b"""

    for v in tri:
        if v != a and v != b:
            return v
    return None


def _ClassifyAngles(face, n, points):
    """Return vector of anglekinds of the Angle around each point in face."""

    return [_AngleKind(face[(i - 1) % n], face[i], face[(i + 1) % n], points)
            for i in list(range(0, n))]


def _AngleKind(a, b, c, points):
    """Return one of the Ang... constants to classify Angle formed by ABC,
    in a counterclockwise traversal of a face,
    where a, b, c are indices into points."""

    if Ccw(a, b, c, points):
        return Angconvex
    elif Ccw(a, c, b, points):
        return Angreflex
    else:
        vb = points.pos[b]
        udotv = Dot2(Sub2(vb, points.pos[a]), Sub2(points.pos[c], vb))
        if udotv > 0.0:
            return Angtangential
        else:
            return Ang0   # to fix: return Ang360 if "inside" spur


def _Quandrangulate(tris, bord, points):
    """Tris is list of triangles, forming a triangulation of region whose
    border edges are in set bord.
    Combine adjacent triangles to make quads, trying for "good" quads where
    possible. Some triangles will probably remain uncombined"""

    (er, td) = _ERGraph(tris, bord, points)
    if len(er) == 0:
        return tris
    if len(er) > GTHRESH:
        match = _GreedyMatch(er)
    else:
        match = _MaxMatch(er)
    return _RemoveEdges(tris, match)


def _RemoveEdges(tris, match):
    """tris is list of triangles.
    er is as returned from _MaxMatch or _GreedyMatch.

    Return list of (A,D,B,C) resulting from deleting edge (A,B) causing a merge
    of two triangles; append to that list the remaining unmatched triangles."""

    ans = []
    triset = set(tris)
    while len(match) > 0:
        (_, e, tl, tr) = match.pop()
        (a, b) = e
        if tl in triset:
            triset.remove(tl)
        if tr in triset:
            triset.remove(tr)
        c = _OtherVert(tl, a, b)
        d = _OtherVert(tr, a, b)
        if c is None or d is None:
            continue
        ans.append((a, d, b, c))
    return ans + list(triset)


def _ERGraph(tris, bord, points):
    """Make an 'Edge Removal Graph'.

    Given a list of triangles, the 'Edge Removal Graph' is a graph whose
    nodes are the triangles (think of a point in the center of them),
    and whose edges go between adjacent triangles (they share a non-border
    edge), such that it would be possible to remove the shared edge
    and form a convex quadrilateral.  Forming a quadrilateralization
    is then a matter of finding a matching (set of edges that don't
    share a vertex - remember, these are the 'face' vertices).
    For better quadrilaterlization, we'll make the Edge Removal Graph
    edges have weights, with higher weights going to the edges that
    are more desirable to remove.  Then we want a maximum weight matching
    in this graph.

    We'll return the graph in a kind of implicit form, using edges of
    the original triangles as a proxy for the edges between the faces
    (i.e., the edge of the triangle is the shared edge). We'll arbitrarily
    pick the triangle graph edge with lower-index start vertex.
    Also, to aid in traversing the implicit graph, we'll keep the left
    and right triangle triples with edge 'ER edge'.
    Finally, since we calculate it anyway, we'll return a dictionary
    mapping edges of the triangles to the triangle triples they're in.

    Args:
      tris: list of (int, int, int) giving a triple of vertex indices for
          triangles, assumed CCW oriented
      bord: set of (int, int) giving vertex indices for border edges
      points: geom.Points - for mapping vertex indices to coords
    Returns:
      (list of (weight,e,tl,tr), dict)
        where edge e=(a,b) is non-border edge
        with left face tl and right face tr (each a triple (i,j,k)),
        where removing the edge would form an "OK" quad (no concave angles),
        with weight representing the desirability of removing the edge
        The dict maps int pairs (a,b) to int triples (i,j,k), that is,
        mapping edges to their containing triangles.
    """

    td = _TriDict(tris)
    dd = _DegreeDict(tris)
    ans = []
    ctris = tris[:]  # copy, so argument not affected
    while len(ctris) > 0:
        (i, j, k) = tl = ctris.pop()
        for e in [(i, j), (j, k), (k, i)]:
            if e in bord:
                continue
            (a, b) = e
            # just consider one of (a,b) and (b,a), to avoid dups
            if a > b:
                continue
            erev = (b, a)
            tr = td.get(erev)
            if not tr:
                continue
            c = _OtherVert(tl, a, b)
            d = _OtherVert(tr, a, b)
            if c is None or d is None:
                continue
            # calculate amax, the max of the new angles that would
            # be formed at a and b if tl and tr were combined
            amax = max(Angle(c, a, b, points) + Angle(d, a, b, points),
                       Angle(c, b, a, points) + Angle(d, b, a, points))
            if amax > 180.0:
                continue
            weight = ANGFAC * (180.0 - amax) + DEGFAC * (dd[a] + dd[b])
            ans.append((weight, e, tl, tr))
    return (ans, td)


def _GreedyMatch(er):
    """er is list of (weight,e,tl,tr).

    Find maximal set so that each triangle appears in at most
    one member of set"""

    # sort in order of decreasing weight
    er.sort(key=lambda v: v[0], reverse=True)
    match = set()
    ans = []
    while len(er) > 0:
        (_, _, tl, tr) = q = er.pop()
        if tl not in match and tr not in match:
            match.add(tl)
            match.add(tr)
            ans.append(q)
    return ans


def _MaxMatch(er):
    """Like _GreedyMatch, but use divide and conquer to find best possible set.

    Args:
      er: list of (weight,e,tl,tr)  - see _ERGraph
    Returns:
      list that is a subset of er giving a maximum weight match
    """

    (ans, _) = _DCMatch(er)
    return ans


def _DCMatch(er):
    """Recursive helper for _MaxMatch.

    Divide and Conquer approach to finding max weight matching.
    If we're lucky, there's an edge in er that separates the edge removal
    graph into (at least) two separate components.  Then the max weight
    is either one that includes that edge or excludes it - and we can
    use a recursive call to _DCMatch to handle each component separately
    on what remains of the graph after including/excluding the separating edge.
    If we're not lucky, we fall back on _EMatch (see below).

    Args:
      er: list of (weight, e, tl, tr) (see _ERGraph)
    Returns:
      (list of (weight, e, tl, tr), float) - the subset forming a maximum
          matching, and the total weight of the match.
    """

    if not er:
        return ([], 0.0)
    if len(er) == 1:
        return (er, er[0][0])
    match = []
    matchw = 0.0
    for i in range(0, len(er)):
        (nc, comp) = _FindComponents(er, i)
        if nc == 1:
            # er[i] doesn't separate er
            continue
        (wi, _, tl, tr) = er[i]
        if comp[tl] != comp[tr]:
            # case 1: er separates graph
            # compare the matches that include er[i] versus
            # those that exclude it
            (a, b) = _PartitionComps(er, comp, i, comp[tl], comp[tr])
            ax = _CopyExcluding(a, tl, tr)
            bx = _CopyExcluding(b, tl, tr)
            (axmatch, wax) = _DCMatch(ax)
            (bxmatch, wbx) = _DCMatch(bx)
            if len(ax) == len(a):
                wa = wax
                amatch = axmatch
            else:
                (amatch, wa) = _DCMatch(a)
            if len(bx) == len(b):
                wb = wbx
                bmatch = bxmatch
            else:
                (bmatch, wb) = _DCMatch(b)
            w = wa + wb
            wx = wax + wbx + wi
            if w > wx:
                match = amatch + bmatch
                matchw = w
            else:
                match = [er[i]] + axmatch + bxmatch
                matchw = wx
        else:
            # case 2: er not needed to separate graph
            (a, b) = _PartitionComps(er, comp, -1, 0, 0)
            (amatch, wa) = _DCMatch(a)
            (bmatch, wb) = _DCMatch(b)
            match = amatch + bmatch
            matchw = wa + wb
        if match:
            break
    if not match:
        return _EMatch(er)
    return (match, matchw)


def _EMatch(er):
    """Exhaustive match helper for _MaxMatch.

    This is the case when we were unable to find a single edge
    separating the edge removal graph into two components.
    So pick a single edge and try _DCMatch on the two cases of
    including or excluding that edge.  We may be lucky in these
    subcases (say, if the graph is currently a simple cycle, so
    only needs one more edge after the one we pick here to separate
    it into components).  Otherwise, we'll end up back in _EMatch
    again, and the worse case will be exponential.

    Pick a random edge rather than say, the first, to hopefully
    avoid some pathological cases.

    Args:
      er: list of (weight, el, tl, tr) (see _ERGraph)
    Returns:
       (list of (weight, e, tl, tr), float) - the subset forming a maximum
          matching, and the total weight of the match.
    """

    if not er:
        return ([], 0.0)
    if len(er) == 1:
        return (er, er[1][1])
    i = random.randint(0, len(er) - 1)
    eri = (wi, _, tl, tr) = er[i]
    # case a: include eri.  exlude other edges that touch tl or tr
    a = _CopyExcluding(er, tl, tr)
    a.append(eri)
    (amatch, wa) = _DCMatch(a)
    wa += wi
    if len(a) == len(er) - 1:
        # if a excludes only eri, then er didn't touch anything else
        # in the graph, and the best match will always include er
        # and we can skip the call for case b
        wb = -1.0
        bmatch = []
    else:
        b = er[:i] + er[i + 1:]
        (bmatch, wb) = _DCMatch(b)
    if wa > wb:
        match = amatch
        match.append(eri)
        matchw = wa
    else:
        match = bmatch
        matchw = wb
    return (match, matchw)


def _FindComponents(er, excepti):
    """Find connected components induced by edges, excluding one edge.

    Args:
      er: list of (weight, el, tl, tr) (see _ERGraph)
      excepti: index in er of edge to be excluded
    Returns:
      (int, dict): int is number of connected components found,
          dict maps triangle triple ->
              connected component index (starting at 1)
     """

    ncomps = 0
    comp = dict()
    for i in range(0, len(er)):
        (_, _, tl, tr) = er[i]
        for t in [tl, tr]:
            if t not in comp:
                ncomps += 1
                _FCVisit(er, excepti, comp, t, ncomps)
    return (ncomps, comp)


def _FCVisit(er, excepti, comp, t, compnum):
    """Helper for _FindComponents depth-first-search."""

    comp[t] = compnum
    for i in range(0, len(er)):
        if i == excepti:
            continue
        (_, _, tl, tr) = er[i]
        if tl == t or tr == t:
            s = tl
            if s == t:
                s = tr
            if s not in comp:
                _FCVisit(er, excepti, comp, s, compnum)


def _PartitionComps(er, comp, excepti, compa, compb):
    """Partition the edges of er by component number, into two lists.

    Generally, put odd components into first list and even into second,
    except that component compa goes in the first and compb goes in the second,
    and we ignore edge er[excepti].

    Args:
      er: list of (weight, el, tl, tr) (see _ERGraph)
      comp: dict - mapping triangle triple -> connected component index
      excepti: int - index in er to ignore (unless excepti==-1)
      compa: int - component to go in first list of answer (unless 0)
      compb: int - component to go in second list of answer (unless 0)
    Returns:
      (list, list) - a partition of er according to above rules
    """

    parta = []
    partb = []
    for i in range(0, len(er)):

        if i == excepti:
            continue
        tl = er[i][2]
        c = comp[tl]
        if c == compa or (c != compb and (c & 1) == 1):
            parta.append(er[i])
        else:
            partb.append(er[i])
    return (parta, partb)


def _CopyExcluding(er, s, t):
    """Return a copy of er, excluding all those involving triangles s and t.

    Args:
      er: list of (weight, e, tl, tr) - see _ERGraph
      s: 3-tuple of int - a triangle
      t: 3-tuple of int - a triangle
    Returns:
      Copy of er excluding those with tl or tr == s or t
    """

    ans = []
    for e in er:
        (_, _, tl, tr) = e
        if tl == s or tr == s or tl == t or tr == t:
            continue
        ans.append(e)
    return ans


def _DegreeDict(tris):
    """Return a dictionary mapping vertices in tris to the number of triangles
    that they are touch."""

    ans = dict()
    for t in tris:
        for v in t:
            if v in ans:
                ans[v] = ans[v] + 1
            else:
                ans[v] = 1
    return ans


def PolygonPlane(face, points):
    """Return a Normal vector for the face with 3d coords given by indexing
    into points."""

    if len(face) < 3:
        return (0.0, 0.0, 1.0)    # arbitrary, we really have no idea
    else:
        coords = [points.pos[i] for i in face]
        return Normal(coords)


# This Normal appears to be on the CCW-traversing side of a polygon
def Normal(coords):
    """Return an average Normal vector for the point list, 3d coords."""

    if len(coords) < 3:
        return (0.0, 0.0, 1.0)    # arbitrary

    (ax, ay, az) = coords[0]
    (bx, by, bz) = coords[1]
    (cx, cy, cz) = coords[2]

    if len(coords) == 3:
        sx = (ay - by) * (az + bz) + \
            (by - cy) * (bz + cz) + \
            (cy - ay) * (cz + az)
        sy = (az - bz) * (ax + bx) + \
            (bz - cz) * (bx + cx) + \
            (cz - az) * (cx + ax)
        sz = (ax - bx) * (by + by) + \
            (bx - cx) * (by + cy) + \
            (cx - ax) * (cy + ay)
        return Norm3(sx, sy, sz)
    else:
        sx = (ay - by) * (az + bz) + (by - cy) * (bz + cz)
        sy = (az - bz) * (ax + bx) + (bz - cz) * (bx + cx)
        sz = (ax - bx) * (ay + by) + (bx - cx) * (by + cy)
        return _NormalAux(coords[3:], coords[0], sx, sy, sz)


def _NormalAux(rest, first, sx, sy, sz):
    (ax, ay, az) = rest[0]
    if len(rest) == 1:
        (bx, by, bz) = first
    else:
        (bx, by, bz) = rest[1]
    nx = sx + (ay - by) * (az + bz)
    ny = sy + (az - bz) * (ax + bx)
    nz = sz + (ax - bx) * (ay + by)
    if len(rest) == 1:
        return Norm3(nx, ny, nz)
    else:
        return _NormalAux(rest[1:], first, nx, ny, nz)


def Norm3(x, y, z):
    """Return vector (x,y,z) normalized by dividing by squared length.
    Return (0.0, 0.0, 1.0) if the result is undefined."""
    sqrlen = x * x + y * y + z * z
    if sqrlen < 1e-100:
        return (0.0, 0.0, 1.0)
    else:
        try:
            d = sqrt(sqrlen)
            return (x / d, y / d, z / d)
        except:
            return (0.0, 0.0, 1.0)


# We're using right-hand coord system, where
# forefinger=x, middle=y, thumb=z on right hand.
# Then, e.g., (1,0,0) x (0,1,0) = (0,0,1)
def Cross3(a, b):
    """Return the cross product of two vectors, a x b."""

    (ax, ay, az) = a
    (bx, by, bz) = b
    return (ay * bz - az * by, az * bx - ax * bz, ax * by - ay * bx)


def Dot2(a, b):
    """Return the dot product of two 2d vectors, a . b."""

    return a[0] * b[0] + a[1] * b[1]


def Perp2(a, b):
    """Return a sort of 2d cross product."""

    return a[0] * b[1] - a[1] * b[0]


def Sub2(a, b):
    """Return difference of 2d vectors, a-b."""

    return (a[0] - b[0], a[1] - b[1])


def Add2(a, b):
    """Return the sum of 2d vectors, a+b."""

    return (a[0] + b[0], a[1] + b[1])


def Length2(v):
    """Return length of vector v=(x,y)."""

    return sqrt(v[0] * v[0] + v[1] * v[1])


def LinInterp2(a, b, alpha):
    """Return the point alpha of the way from a to b."""

    beta = 1 - alpha
    return (beta * a[0] + alpha * b[0], beta * a[1] + alpha * b[1])


def Normalized2(p):
    """Return vector p normlized by dividing by its squared length.
    Return (0.0, 1.0) if the result is undefined."""

    (x, y) = p
    sqrlen = x * x + y * y
    if sqrlen < 1e-100:
        return (0.0, 1.0)
    else:
        try:
            d = sqrt(sqrlen)
            return (x / d, y / d)
        except:
            return (0.0, 1.0)


def Angle(a, b, c, points):
    """Return Angle abc in degrees, in range [0,180),
    where a,b,c are indices into points."""

    u = Sub2(points.pos[c], points.pos[b])
    v = Sub2(points.pos[a], points.pos[b])
    n1 = Length2(u)
    n2 = Length2(v)
    if n1 == 0.0 or n2 == 0.0:
        return 0.0
    else:
        costheta = Dot2(u, v) / (n1 * n2)
        if costheta > 1.0:
            costheta = 1.0
        if costheta < - 1.0:
            costheta = - 1.0
        return math.acos(costheta) * 180.0 / math.pi


def SegsIntersect(ixa, ixb, ixc, ixd, points):
    """Return true if segment AB intersects CD,
    false if they just touch.  ixa, ixb, ixc, ixd are indices
    into points."""

    a = points.pos[ixa]
    b = points.pos[ixb]
    c = points.pos[ixc]
    d = points.pos[ixd]
    u = Sub2(b, a)
    v = Sub2(d, c)
    w = Sub2(a, c)
    pp = Perp2(u, v)
    if abs(pp) > TOL:
        si = Perp2(v, w) / pp
        ti = Perp2(u, w) / pp
        return 0.0 < si < 1.0 and 0.0 < ti < 1.0
    else:
        # parallel or overlapping
        if Dot2(u, u) == 0.0 or Dot2(v, v) == 0.0:
            return False
        else:
            pp2 = Perp2(w, v)
            if abs(pp2) > TOL:
                return False  # parallel, not collinear
            z = Sub2(b, c)
            (vx, vy) = v
            (wx, wy) = w
            (zx, zy) = z
            if vx == 0.0:
                (t0, t1) = (wy / vy, zy / vy)
            else:
                (t0, t1) = (wx / vx, zx / vx)
            return 0.0 < t0 < 1.0 and 0.0 < t1 < 1.0


def Ccw(a, b, c, points):
    """Return true if ABC is a counterclockwise-oriented triangle,
    where a, b, and c are indices into points.
    Returns false if not, or if colinear within TOL."""

    (ax, ay) = (points.pos[a][0], points.pos[a][1])
    (bx, by) = (points.pos[b][0], points.pos[b][1])
    (cx, cy) = (points.pos[c][0], points.pos[c][1])
    d = ax * by - bx * ay - ax * cy + cx * ay + bx * cy - cx * by
    return d > TOL


def InCircle(a, b, c, d, points):
    """Return true if circle through points with indices a, b, c
    contains point with index d (indices into points).
    Except: if ABC forms a counterclockwise oriented triangle
    then the test is reversed: return true if d is outside the circle.
    Will get false, no matter what orientation, if d is cocircular, with TOL^2.
      | xa ya xa^2+ya^2 1 |
      | xb yb xb^2+yb^2 1 | > 0
      | xc yc xc^2+yc^2 1 |
      | xd yd xd^2+yd^2 1 |
    """

    (xa, ya, za) = _Icc(points.pos[a])
    (xb, yb, zb) = _Icc(points.pos[b])
    (xc, yc, zc) = _Icc(points.pos[c])
    (xd, yd, zd) = _Icc(points.pos[d])
    det = xa * (yb * zc - yc * zb - yb * zd + yd * zb + yc * zd - yd * zc) \
        - xb * (ya * zc - yc * za - ya * zd + yd * za + yc * zd - yd * zc) \
        + xc * (ya * zb - yb * za - ya * zd + yd * za + yb * zd - yd * zb) \
        - xd * (ya * zb - yb * za - ya * zc + yc * za + yb * zc - yc * zb)
    return det > TOL * TOL


def _Icc(p):
    (x, y) = (p[0], p[1])
    return (x, y, x * x + y * y)

# ====================================================================================
#       OFFSET FUNCTIONS
# ====================================================================================

AREATOL = 1e-4


class Spoke(object):
    """A Spoke is a line growing from an outer vertex to an inner one.

    A Spoke is contained in an Offset (see below).

    Attributes:
      origin: int - index of origin point in a Points
      dest: int - index of dest point
      is_reflex: bool - True if spoke grows from a reflex angle
      dir: (float, float, float) - direction vector (normalized)
      speed: float - at time t, other end of spoke is
          origin + t*dir.  Speed is such that the wavefront
          from the face edges moves at speed 1.
      face: int - index of face containing this Spoke, in Offset
      index: int - index of this Spoke in its face
      destindex: int - index of Spoke dest in its face
    """

    def __init__(self, v, prev, next, face, index, points):
        """Set attribute of spoke from points making up initial angle.

        The spoke grows from an angle inside a face along the bisector
        of that angle.  Its speed is 1/sin(.5a), where a is the angle
        formed by (prev, v, next).  That speed means that the perpendicular
        from the end of the spoke to either of the prev->v or v->prev
        edges will grow at speed 1.

        Args:
          v: int - index of point spoke grows from
          prev: int - index of point before v on boundary (in CCW order)
          next: int - index of point after v on boundary (in CCW order)
          face: int - index of face containing this spoke, in containing offset
          index: int - index of this spoke in its face
          points: geom.Points - maps vertex indices to 3d coords
        """

        self.origin = v
        self.dest = v
        self.face = face
        self.index = index
        self.destindex = -1
        vmap = points.pos
        vp = vmap[v]
        prevp = vmap[prev]
        nextp = vmap[next]
        uin = Normalized2(Sub2(vp, prevp))
        uout = Normalized2(Sub2(nextp, vp))
        uavg = Normalized2((0.5 * (uin[0] + uout[0]),
                            0.5 * (uin[1] + uout[1])))
        if abs(Length2(uavg)) < TOL:
            # in and out vectors are reverse of each other
            self.dir = (uout[0], uout[1], 0.0)
            self.is_reflex = False
            self.speed = 1e7
        else:
            # bisector direction is 90 degree CCW rotation of
            # average incoming/outgoing
            self.dir = (-uavg[1], uavg[0], 0.0)
            self.is_reflex = Ccw(next, v, prev, points)
            ang = Angle(prev, v, next, points)  # in range [0, 180)
            sin_half_ang = math.sin(math.pi * ang / 360.0)
            if abs(sin_half_ang) < TOL:
                self.speed = 1e7
            else:
                self.speed = 1.0 / sin_half_ang

    def __repr__(self):
        """Printing representation of a Spoke."""

        return "@%d+%gt%s <%d,%d>" % (self.origin,
                                      self.speed, str(self.dir),
                                      self.face, self.index)

    def EndPoint(self, t, points, vspeed):
        """Return the coordinates of the non-origin point at time t.

        Args:
          t: float - time to end of spoke
          points: geom.Points - coordinate map
          vspeed: float - speed in z direction
        Returns:
          (float, float, float) - coords of spoke's endpoint at time t
        """

        p = points.pos[self.origin]
        d = self.dir
        v = self.speed
        return (p[0] + v * t * d[0], p[1] + v * t * d[1], p[2] + vspeed * t)

    def VertexEvent(self, other, points):
        """Intersect self with other spoke, and return the OffsetEvent, if any.

        A vertex event is with one advancing spoke intersects an adjacent
        adavancing spoke, forming a new vertex.

        Args:
          other: Spoke - other spoke to intersect with
          points: Geom.points
        Returns:
          None or OffsetEvent - if there's an intersection in the growing
            directions of the spokes, will return the OffsetEvent for
            the intersection;
            if lines are collinear or parallel, return None
        """

        vmap = points.pos
        a = vmap[self.origin]
        b = Add2(a, self.dir)
        c = vmap[other.origin]
        d = Add2(c, other.dir)
        # find intersection of line ab with line cd
        u = Sub2(b, a)
        v = Sub2(d, c)
        w = Sub2(a, c)
        pp = Perp2(u, v)
        if abs(pp) > TOL:
            # lines or neither parallel nor collinear
            si = Perp2(v, w) / pp
            ti = Perp2(u, w) / pp
            if si >= 0 and ti >= 0:
                p = LinInterp2(a, b, si)
                dist_ab = si * Length2(u)
                dist_cd = ti * Length2(v)
                time_ab = dist_ab / self.speed
                time_cd = dist_cd / other.speed
                time = max(time_ab, time_cd)
                return OffsetEvent(True, time, p, self, other)
        return None

    def EdgeEvent(self, other, offset):
        """Intersect self with advancing edge and return OffsetEvent, if any.

        An edge event is when one advancing spoke intersects an advancing
        edge.  Advancing edges start out as face edges and move perpendicular
        to them, at a rate of 1.  The endpoints of the edge are the advancing
        spokes on either end of the edge (so the edge shrinks or grows as
        it advances). At some time, the edge may shrink to nothing and there
        will be no EdgeEvent after that time.

        We represent an advancing edge by the first spoke (in CCW order
        of face) of the pair of defining spokes.

        At time t, end of this spoke is at
            o + d*s*t
        where o=self.origin, d=self.dir, s= self.speed.
        The advancing edge line has this equation:
            oo + od*os*t + p*a
        where oo, od, os are o, d, s for other spoke, and p is direction
        vector parallel to advancing edge, and a is a real parameter.
        Equating x and y of intersection point:

            o.x + d.x*s*t = oo.x + od.x*os*t + p.x*w
            o.y + d.y*s*t = oo.y + od.y*os*t + p.y*w

        which can be rearranged into the form

            a = bt + cw
            d = et + fw

        and solved for t, w.

        Args:
          other: Spoke - the edge out of this spoke's origin is the advancing
              edge to be checked for intersection
          offset: Offset - the containing Offset
        Returns:
          None or OffsetEvent - with data about the intersection, if any
        """

        vmap = offset.polyarea.points.pos
        o = vmap[self.origin]
        oo = vmap[other.origin]
        otherface = offset.facespokes[other.face]
        othernext = otherface[(other.index + 1) % len(otherface)]
        oonext = vmap[othernext.origin]
        p = Normalized2(Sub2(oonext, oo))
        a = o[0] - oo[0]
        d = o[1] - oo[1]
        b = other.dir[0] * other.speed - self.dir[0] * self.speed
        e = other.dir[1] * other.speed - self.dir[1] * self.speed
        c = p[0]
        f = p[1]
        if abs(c) > TOL:
            dem = e - f * b / c
            if abs(dem) > TOL:
                t = (d - f * a / c) / dem
                w = (a - b * t) / c
            else:
                return None
        elif abs(f) > TOL:
            dem = b - c * e / f
            if abs(dem) > TOL:
                t = (a - c * d / f) / dem
                w = (d - e * t) / f
            else:
                return None
        else:
            return None
        if t < 0.0:
            # intersection is in backward direction along self spoke
            return None
        if w < 0.0:
            # intersection on wrong side of first end of advancing line segment
            return None
        # calculate the equivalent of w for the other end
        aa = o[0] - oonext[0]
        dd = o[1] - oonext[1]
        bb = othernext.dir[0] * othernext.speed - self.dir[0] * self.speed
        ee = othernext.dir[1] * othernext.speed - self.dir[1] * self.speed
        cc = -p[0]
        ff = -p[1]
        if abs(cc) > TOL:
            ww = (aa - bb * t) / cc
        elif abs(ff) > TOL:
            ww = (dd - ee * t) / ff
        else:
            return None
        if ww < 0.0:
            return None
        evertex = (o[0] + self.dir[0] * self.speed * t,
                   o[1] + self.dir[1] * self.speed * t)
        return OffsetEvent(False, t, evertex, self, other)


class OffsetEvent(object):
    """An event involving a spoke during offset computation.

    The events kinds are:
      vertex event: the spoke intersects an adjacent spoke and makes a new
          vertex
      edge event: the spoke hits an advancing edge and splits it

    Attributes:
      is_vertex_event: True if this is a vertex event (else it is edge event)
      time: float - time at which it happens (edges advance at speed 1)
      event_vertex: (float, float) - intersection point of event
      spoke: Spoke - the spoke that this event is for
      other: Spoke - other spoke involved in event; if vertex event, this will
        be an adjacent spoke that intersects; if an edge event, this is the
        spoke whose origin's outgoing edge grows to hit this event's spoke
    """

    def __init__(self, isv, time, evertex, spoke, other):
        """Creates and initializes attributes of an OffsetEvent."""

        self.is_vertex_event = isv
        self.time = time
        self.event_vertex = evertex
        self.spoke = spoke
        self.other = other

    def __repr__(self):
        """Printing representation of an event."""

        if self.is_vertex_event:
            c = "V"
        else:
            c = "E"
        return "%s t=%5f %s %s %s" % (c, self.time, str(self.event_vertex),
                                      repr(self.spoke), repr(self.other))


class Offset(object):
    """Represents an offset polygonal area, and used to construct one.

    Currently, the polygonal area must lie approximately in the XY plane.
    As well as growing inwards in that plane, the advancing lines also
    move in the Z direction at the rate of vspeed.

    Attributes:
      polyarea: geom.PolyArea - the area we are offsetting from.
          We share the polyarea.points, and add to it as points in
          the offset polygonal area are computed.
      facespokes: list of list of Spoke - each sublist is a closed face
          (oriented CCW); the faces may mutually interfere.
          These lists are spokes for polyarea.poly + polyarea.holes.
      endtime: float - time when this offset hits its first
          event (relative to beginning of this offset), or the amount
          that takes this offset to the end of the total Build time
      timesofar: float - sum of times taken by all containing Offsets
      vspeed: float - speed that edges move perpendicular to offset plane
      inneroffsets: list of Offset - the offsets that take over after this
          (inside it)
    """

    def __init__(self, polyarea, time, vspeed):
        """Set up initial state of Offset from a polyarea.

        Args:
          polyarea: geom.PolyArea
          time: float - time so far
        """

        self.polyarea = polyarea
        self.facespokes = []
        self.endtime = 0.0
        self.timesofar = time
        self.vspeed = vspeed
        self.inneroffsets = []
        self.InitFaceSpokes(polyarea.poly)
        for f in polyarea.holes:
            self.InitFaceSpokes(f)

    def __repr__(self):
        ans = ["Offset: endtime=%g" % self.endtime]
        for i, face in enumerate(self.facespokes):
            ans.append(("<%d>" % i) + str([str(spoke) for spoke in face]))
        return '\n'.join(ans)

    def PrintNest(self, indent_level=0):
        indent = " " * indent_level * 4
        print(indent + "Offset  timesofar=", self.timesofar, "endtime=",
              self.endtime)
        print(indent + " polyarea=", self.polyarea.poly, self.polyarea.holes)
        for o in self.inneroffsets:
            o.PrintNest(indent_level + 1)

    def InitFaceSpokes(self, face_vertices):
        """Initialize the offset representation of a face from vertex list.

        If the face has no area or too small an area, don't bother making it.

        Args:
          face_vertices: list of int - point indices for boundary of face
        Side effect:
          A new face (list of spokes) may be added to self.facespokes
        """

        n = len(face_vertices)
        if n <= 2:
            return
        points = self.polyarea.points
        area = abs(SignedArea(face_vertices, points))
        if area < AREATOL:
            return
        findex = len(self.facespokes)
        fspokes = [Spoke(v, face_vertices[(i - 1) % n],
                         face_vertices[(i + 1) % n], findex, i, points)
                   for i, v in enumerate(face_vertices)]
        self.facespokes.append(fspokes)

    def NextSpokeEvents(self, spoke):
        """Return the OffsetEvents that will next happen for a given spoke.

        It might happen that some events happen essentially simultaneously,
        and also it is convenient to separate Edge and Vertex events, so
        we return two lists.
        But, for vertex events, only look at the event with the next Spoke,
        as the event with the previous spoke will be accounted for when we
        consider that previous spoke.

        Args:
          spoke: Spoke - a spoke in one of the faces of this object
        Returns:
          (float, list of OffsetEvent, list of OffsetEvent) -
              time of next event,
              next Vertex event list and next Edge event list
        """

        facespokes = self.facespokes[spoke.face]
        n = len(facespokes)
        bestt = 1e100
        bestv = []
        beste = []
        # First find vertex event (only the one with next spoke)
        next_spoke = facespokes[(spoke.index + 1) % n]
        ev = spoke.VertexEvent(next_spoke, self.polyarea.points)
        if ev:
            bestv = [ev]
            bestt = ev.time
        # Now find edge events, if this is a reflex vertex
        if spoke.is_reflex:
            prev_spoke = facespokes[(spoke.index - 1) % n]
            for f in self.facespokes:
                for other in f:
                    if other == spoke or other == prev_spoke:
                        continue
                    ev = spoke.EdgeEvent(other, self)
                    if ev:
                        if ev.time < bestt - TOL:
                            beste = []
                            bestv = []
                            bestt = ev.time
                        if abs(ev.time - bestt) < TOL:
                            beste.append(ev)
        return (bestt, bestv, beste)

    def Build(self, target=2e100):
        """Build the complete Offset structure or up until target time.

        Find the next event(s), makes the appropriate inner Offsets
        that are inside this one, and calls Build on those Offsets to continue
        the process until only a single point is left or time reaches target.
        """

        bestt = 1e100
        bestevs = [[], []]
        for f in self.facespokes:
            for s in f:
                (t, ve, ee) = self.NextSpokeEvents(s)
                if t < bestt - TOL:
                    bestevs = [[], []]
                    bestt = t
                if abs(t - bestt) < TOL:
                    bestevs[0].extend(ve)
                    bestevs[1].extend(ee)
        if bestt == 1e100:
            # could happen if polygon is oriented wrong
            # or in other special cases
            return
        if abs(bestt) < TOL:
            # seems to be in a loop, so quit
            return
        self.endtime = bestt
        (ve, ee) = bestevs
        newfaces = []
        splitjoin = None
        if target < self.endtime:
            self.endtime = target
            newfaces = self.MakeNewFaces(self.endtime)
        elif ve and not ee:
            # Only vertex events.
            # Merging of successive vertices in inset face will
            # take care of the vertex events
            newfaces = self.MakeNewFaces(self.endtime)
        else:
            # Edge events too
            # First make the new faces (handles all vertex events)
            newfaces = self.MakeNewFaces(self.endtime)
            # Only do one edge event (handle other simultaneous edge
            # events in subsequent recursive Build calls)
            splitjoin = self.SplitJoinFaces(newfaces, ee[0])
        nexttarget = target - self.endtime
        if len(newfaces) > 0:
            pa = PolyArea(points=self.polyarea.points)
            pa.data = self.polyarea.data
            newt = self.timesofar + self.endtime
            pa2 = None  # may make another
            if not splitjoin:
                pa.poly = newfaces[0]
                pa.holes = newfaces[1:]
            elif splitjoin[0] == 'split':
                (_, findex, newface0, newface1) = splitjoin
                if findex == 0:
                    # Outer poly of polyarea was split.
                    # Now there will be two polyareas.
                    # If there were holes, need to allocate according to
                    # which one contains the holes.
                    pa.poly = newface0
                    pa2 = PolyArea(points=self.polyarea.points)
                    pa2.data = self.polyarea.data
                    pa2.poly = newface1
                    if len(newfaces) > 1:
                        # print("need to allocate holes")
                        for hf in newfaces[1:]:
                            if pa.ContainsPoly(hf, self.polyarea.points):
                                # print("add", hf, "to", pa.poly)
                                pa.holes.append(hf)
                            elif pa2.ContainsPoly(hf, self.polyarea.points):
                                # print("add", hf, "to", pa2.poly)
                                pa2.holes.append(hf)
                            else:
                                print("whoops, hole in neither poly!")
                    self.inneroffsets = [Offset(pa, newt, self.vspeed),
                                         Offset(pa2, newt, self.vspeed)]
                else:
                    # A hole was split. New faces just replace the split one.
                    pa.poly = newfaces[0]
                    pa.holes = newfaces[0:findex] + [newface0, newface1] + \
                        newfaces[findex + 1:]
            else:
                # A join
                (_, findex, othfindex, newface0) = splitjoin
                if findex == 0 or othfindex == 0:
                    # Outer poly was joined to one hole.
                    pa.poly = newface0
                    pa.holes = [f for f in newfaces if f is not None]
                else:
                    # Two holes were joined
                    pa.poly = newfaces[0]
                    pa.holes = [f for f in newfaces if f is not None] + \
                        [newface0]
            self.inneroffsets = [Offset(pa, newt, self.vspeed)]
            if pa2:
                self.inneroffsets.append(Offset(pa2, newt, self.vspeed))
            if nexttarget > TOL:
                for o in self.inneroffsets:
                    o.Build(nexttarget)

    def FaceAtSpokeEnds(self, f, t):
        """Return a new face that is at the spoke ends of face f at time t.

        Also merges any adjacent approximately equal vertices into one vertex,
        so returned list may be smaller than len(f).
        Also sets the destindex fields of the spokes to the vertex they
        will now end at.

        Args:
          f: list of Spoke - one of self.faces
          t: float - time in this offset
        Returns:
          list of int - indices into self.polyarea.points
          (which has been extended with new ones)
        """

        newface = []
        points = self.polyarea.points
        for i in range(0, len(f)):
            s = f[i]
            vcoords = s.EndPoint(t, points, self.vspeed)
            v = points.AddPoint(vcoords)
            if newface:
                if v == newface[-1]:
                    s.destindex = len(newface) - 1
                elif i == len(f) - 1 and v == newface[0]:
                    s.destindex = 0
                else:
                    newface.append(v)
                    s.destindex = len(newface) - 1
            else:
                newface.append(v)
                s.destindex = 0
            s.dest = v
        return newface

    def MakeNewFaces(self, t):
        """For each face in this offset, make new face extending spokes
        to time t.

        Args:
          t: double - time
        Returns:
          list of list of int - list of new faces
        """

        ans = []
        for f in self.facespokes:
            newf = self.FaceAtSpokeEnds(f, t)
            if len(newf) > 2:
                ans.append(newf)
        return ans

    def SplitJoinFaces(self, newfaces, ev):
        """Use event ev to split or join faces.

        Given ev, an edge event, use the ev spoke to split the
        other spoke's inner edge.
        If the ev spoke's face and other's face are the same, this splits the
        face into two; if the faces are different, it joins them into one.
        We have just made faces at the end of the spokes.
        We have to remove the edge going from the other spoke to its
        next spoke, and replace it with two edges, going to and from
        the event spoke's destination.
        General situation:
             __  s  ____
        c\     b\ | /a       /e
          \      \|/        /
          f----------------g
         /        d        \
       o/                   \h

        where sd is the event spoke and of is the "other spoke",
        hg is a spoke, and cf, fg. ge, ad, and db are edges in
        the new inside face.
        What we are to do is to split fg into two edges, with the
        joining point attached where b,s,a join.
        There are a bunch of special cases:
         - one of split fg edges might have zero length because end points
           are already coincident or nearly coincident.
         - maybe c==b or e==a

        Args:
          newfaces: list of list of int - the new faces
          ev: OffsetEvent - an edge event
        Side Effects:
          faces in newfaces that are involved in split or join are
          set to None
        Returns: one of:
          ('split', int, list of int, list of int) - int is the index in
              newfaces of the face that was split, two lists are the
              split faces
          ('join', int, int, list of int) - two ints are the indices in
              newfaces of the faces that were joined, and the list is
              the joined face
        """

        # print("SplitJoinFaces", newfaces, ev)
        spoke = ev.spoke
        other = ev.other
        findex = spoke.face
        othfindex = other.face
        newface = newfaces[findex]
        othface = newfaces[othfindex]
        nnf = len(newface)
        nonf = len(othface)
        d = spoke.destindex
        f = other.destindex
        c = (f - 1) % nonf
        g = (f + 1) % nonf
        e = (f + 2) % nonf
        a = (d - 1) % nnf
        b = (d + 1) % nnf
        # print("newface=", newface)
        # if findex != othfindex: print("othface=", othface)
        # print("d=", d, "f=", f, "c=", c, "g=", g, "e=", e, "a=", a, "b=", b)
        newface0 = []
        newface1 = []
        # The two new faces put spoke si's dest on edge between
        # pi's dest and qi (edge after pi)'s dest in original face.
        # These are indices in the original face; the current dest face
        # may have fewer elements because of merging successive points
        if findex == othfindex:
            # Case where splitting one new face into two.
            # The new new faces are:
            # [d, g, e, ..., a] and [d, b, ..., c, f]
            # (except we actually want the vertex numbers at those positions)
            newface0 = [newface[d]]
            i = g
            while i != d:
                newface0.append(newface[i])
                i = (i + 1) % nnf
            newface1 = [newface[d]]
            i = b
            while i != f:
                newface1.append(newface[i])
                i = (i + 1) % nnf
            newface1.append(newface[f])
            # print("newface0=", newface0, "newface1=", newface1)
            # now the destindex values for the spokes are messed up
            # but I don't think we need them again
            newfaces[findex] = None
            return ('split', findex, newface0, newface1)
        else:
            # Case where joining two faces into one.
            # The new face is splicing d's face between
            # f and g in other face (or the reverse of all of that).
            newface0 = [othface[i] for i in range(0, f + 1)]
            newface0.append(newface[d])
            i = b
            while i != d:
                newface0.append(newface[i])
                i = (i + 1) % nnf
            newface0.append(newface[d])
            if g != 0:
                newface0.extend([othface[i] for i in range(g, nonf)])
            # print("newface0=", newface0)
            newfaces[findex] = None
            newfaces[othfindex] = None
            return ('join', findex, othfindex, newface0)

    def InnerPolyAreas(self):
        """Return the interior of the offset (and contained offsets) as
        PolyAreas.

        Returns:
          geom.PolyAreas
        """

        ans = PolyAreas()
        ans.points = self.polyarea.points
        _AddInnerAreas(self, ans)
        return ans

    def MaxAmount(self):
        """Returns the maximum offset amount possible.
        Returns:
          float - maximum amount
        """

        # Need to do Build on a copy of points
        # so don't add points that won't be used when
        # really do a Build with a smaller amount
        test_points = Points()
        test_points.AddPoints(self.polyarea.points)
        save_points = self.polyarea.points
        self.polyarea.points = test_points
        self.Build()
        max_amount = self._MaxTime()
        self.polyarea.points = save_points
        return max_amount

    def _MaxTime(self):
        if self.inneroffsets:
            return max([o._MaxTime() for o in self.inneroffsets])
        else:
            return self.timesofar + self.endtime


def _AddInnerAreas(off, polyareas):
    """Add the innermost areas of offset off to polyareas.

    Assume that polyareas is already using the proper shared points.

    Arguments:
      off: Offset
      polyareas: geom.PolyAreas
    Side Effects:
      Any non-zero-area faces in the very inside of off are
      added to polyareas.
    """

    if off.inneroffsets:
        for o in off.inneroffsets:
            _AddInnerAreas(o, polyareas)
    else:
        newpa = PolyArea(polyareas.points)
        for i, f in enumerate(off.facespokes):
            newface = off.FaceAtSpokeEnds(f, off.endtime)
            area = abs(SignedArea(newface, polyareas.points))
            if area < AREATOL:
                if i == 0:
                    break
                else:
                    continue
            if i == 0:
                newpa.poly = newface
                newpa.data = off.polyarea.data
            else:
                newpa.holes.append(newface)
        if newpa.poly:
            polyareas.polyareas.append(newpa)


# ====================================================================================
#       MODEL FUNCTIONS
# ====================================================================================

def PolyAreasToModel(polyareas, bevel_amount, bevel_pitch, quadrangulate):
    """Convert a PolyAreas into a Model object.

    Assumes polyareas are in xy plane.

    Args:
      polyareas: geom.PolyAreas
      bevel_amount: float - if > 0, amount of bevel
      bevel_pitch: float - if > 0, angle in radians of bevel
      quadrangulate: bool - should n-gons be quadrangulated?
    Returns:
      geom.Model
    """

    m = Model()
    if not polyareas:
        return m
    polyareas.points.AddZCoord(0.0)
    m.points = polyareas.points
    for pa in polyareas.polyareas:
        PolyAreaToModel(m, pa, bevel_amount, bevel_pitch, quadrangulate)
    return m


def PolyAreaToModel(m, pa, bevel_amount, bevel_pitch, quadrangulate):
    if bevel_amount > 0.0:
        BevelPolyAreaInModel(m, pa, bevel_amount, bevel_pitch, quadrangulate,
                             False)
    elif quadrangulate:
        if len(pa.poly) == 0:
            return
        qpa = QuadrangulateFaceWithHoles(pa.poly, pa.holes, pa.points)
        m.faces.extend(qpa)
        m.face_data.extend([pa.data] * len(qpa))
    else:
        m.faces.append(pa.poly)
        # TODO: just the first part of QuadrangulateFaceWithHoles, to join
        # holes to outer poly
        m.face_data.append(pa.data)


def ExtrudePolyAreasInModel(mdl, polyareas, depth, cap_back):
    """Extrude the boundaries given by polyareas by -depth in z.

    Assumes polyareas are in xy plane.

    Arguments:
      mdl: geom.Model - where to do extrusion
      polyareas: geom.Polyareas
      depth: float
      cap_back: bool - if True, cap off the back
    Side Effects:
      For all edges in polys in polyareas, make quads in Model
      extending those edges by depth in the negative z direction.
      The application data will be the data of the face that the edge
      is part of.
    """

    for pa in polyareas.polyareas:
        back_poly = _ExtrudePoly(mdl, pa.poly, depth, pa.data, True)
        back_holes = []
        for p in pa.holes:
            back_holes.append(_ExtrudePoly(mdl, p, depth, pa.data, False))
        if cap_back:
            qpa = QuadrangulateFaceWithHoles(back_poly, back_holes,
                                             polyareas.points)
            # need to reverse each poly to get normals pointing down
            for i, p in enumerate(qpa):
                t = list(p)
                t.reverse()
                qpa[i] = tuple(t)
            mdl.faces.extend(qpa)
            mdl.face_data.extend([pa.data] * len(qpa))


def _ExtrudePoly(mdl, poly, depth, data, isccw):
    """Extrude the poly by -depth in z

    Arguments:
      mdl: geom.Model - where to do extrusion
      poly: list of vertex indices
      depth: float
      data: application data
      isccw: True if counter-clockwise
    Side Effects
      For all edges in poly, make quads in Model
      extending those edges by depth in the negative z direction.
      The application data will be the data of the face that the edge
      is part of.
    Returns:
      list of int - vertices for extruded poly
    """

    if len(poly) < 2:
        return
    extruded_poly = []
    points = mdl.points
    if isccw:
        incr = 1
    else:
        incr = -1
    for i, v in enumerate(poly):
        vnext = poly[(i + incr) % len(poly)]
        (x0, y0, z0) = points.pos[v]
        (x1, y1, z1) = points.pos[vnext]
        vextrude = points.AddPoint((x0, y0, z0 - depth))
        vnextextrude = points.AddPoint((x1, y1, z1 - depth))
        if isccw:
            sideface = [v, vextrude, vnextextrude, vnext]
        else:
            sideface = [v, vnext, vnextextrude, vextrude]
        mdl.faces.append(sideface)
        mdl.face_data.append(data)
        extruded_poly.append(vextrude)
    return extruded_poly


def BevelPolyAreaInModel(mdl, polyarea,
                         bevel_amount, bevel_pitch, quadrangulate, as_percent):
    """Bevel the interior of polyarea in model.

    This does smart beveling: advancing edges are merged
    rather than doing an 'overlap'.  Advancing edges that
    hit an opposite edge result in a split into two beveled areas.

    If the polyarea is not in the xy plane, do the work in a
    transformed model, and then transfer the changes back.

    Arguments:
      mdl: geom.Model - where to do bevel
      polyarea geom.PolyArea - area to bevel into
      bevel_amount: float - if > 0, amount of bevel
      bevel_pitch: float - if > 0, angle in radians of bevel
      quadrangulate: bool - should n-gons be quadrangulated?
      as_percent: bool - if True, interpret amount as percent of max
    Side Effects:
      Faces and points are added to model to model the
      bevel and the interior of the polyareas.
    """

    pa_norm = polyarea.Normal()
    if pa_norm == (0.0, 0.0, 1.0):
        m = mdl
        pa_rot = polyarea
    else:
        (pa_rot, inv_rot, inv_map) = _RotatedPolyAreaToXY(polyarea, pa_norm)
        # don't have to add the original faces into model, just their points.
        m = Model()
        m.points = pa_rot.points
    vspeed = math.tan(bevel_pitch)
    off = Offset(pa_rot, 0.0, vspeed)
    if as_percent:
        bevel_amount = bevel_amount * off.MaxAmount() / 100.0
    off.Build(bevel_amount)
    inner_pas = AddOffsetFacesToModel(m, off, polyarea.data)
    for pa in inner_pas.polyareas:
        if quadrangulate:
            if len(pa.poly) == 0:
                continue
            qpa = QuadrangulateFaceWithHoles(pa.poly, pa.holes,
                                             pa.points)
            m.faces.extend(qpa)
            m.face_data.extend([pa.data] * len(qpa))
        else:
            m.faces.append(pa.poly)
            m.face_data.append(pa.data)
    if m != mdl:
        _AddTransformedPolysToModel(mdl, m.faces, m.points, m.face_data,
                                    inv_rot, inv_map)


def AddOffsetFacesToModel(mdl, off, data=None):
    """Add the faces due to an offset into model.

    Returns the remaining interiors of the offset as a PolyAreas.

    Args:
      mdl: geom.Model - model to add offset faces into
      off: offset.Offset
      data: any - application data to be copied to the faces
    Returns:
      geom.PolyAreas
    """

    mdl.points = off.polyarea.points
    assert(len(mdl.points.pos) == 0 or len(mdl.points.pos[0]) == 3)
    o = off
    ostack = []
    while o:
        if o.endtime != 0.0:
            for face in o.facespokes:
                n = len(face)
                for i, spoke in enumerate(face):
                    nextspoke = face[(i + 1) % n]
                    v0 = spoke.origin
                    v1 = nextspoke.origin
                    v2 = nextspoke.dest
                    v3 = spoke.dest
                    if v2 == v3:
                        mface = [v0, v1, v2]
                    else:
                        mface = [v0, v1, v2, v3]
                    mdl.faces.append(mface)
                    mdl.face_data.append(data)
        ostack.extend(o.inneroffsets)
        if ostack:
            o = ostack.pop()
        else:
            o = None
    return off.InnerPolyAreas()


def BevelSelectionInModel(mdl, bevel_amount, bevel_pitch, quadrangulate,
                          as_region, as_percent):
    """Bevel all the faces in the model, perhaps as one region.

    If as_region is False, each face is beveled individually,
    otherwise regions of contiguous faces are merged into
    PolyAreas and beveled as a whole.

    TODO: something if extracted PolyAreas are not approximately
    planar.

    Args:
      mdl: geom.Model
      bevel_amount: float - amount to inset
      bevel_pitch: float - angle of bevel side
      quadrangulate: bool - should insides be quadrangulated?
      as_region: bool - should faces be merged into regions?
      as_percent: bool - should amount be interpreted as a percent
          of the maximum amount (if True) or an absolute amount?
    Side effect:
      Beveling faces will be added to the model
    """

    pas = []
    if as_region:
        pas = RegionToPolyAreas(mdl.faces, mdl.points, mdl.face_data)
    else:
        for f, face in enumerate(mdl.faces):
            pas.append(PolyArea(mdl.points, face, [],
                                mdl.face_data[f]))
    for pa in pas:
        BevelPolyAreaInModel(mdl, pa,
                             bevel_amount, bevel_pitch, quadrangulate, as_percent)


def RegionToPolyAreas(faces, points, data):
    """Find polygonal outlines induced by union of faces.

    Finds the polygons formed by boundary edges (those not
    sharing an edge with another face in region_faces), and
    turns those into PolyAreas.
    In the general case, there will be holes inside.
    We want to associate data with the region PolyAreas.
    Just choose a representative element of data[] when
    more than one face is combined into a PolyArea.

    Args:
      faces: list of list of int - each sublist is a face (indices into points)
      points: geom.Points - gives coordinates for vertices
      data: list of any - parallel to faces, app data to put in PolyAreas
    Returns:
      list of geom.PolyArea
    """

    ans = []
    (edges, vtoe) = _GetEdgeData(faces)
    (face_adj, is_interior_edge) = _GetFaceGraph(faces, edges, vtoe, points)
    (components, ftoc) = _FindFaceGraphComponents(faces, face_adj)
    for c in range(len(components)):
        boundary_edges = set()
        betodata = dict()
        vstobe = dict()
        for e, ((vs, ve), f) in enumerate(edges):
            if ftoc[f] != c or is_interior_edge[e]:
                continue
            boundary_edges.add(e)
            # vstobe[v] is set of edges leaving v
            # (could be more than one if boundary touches itself at a vertex)
            if vs in vstobe:
                vstobe[vs].append(e)
            else:
                vstobe[vs] = [e]
            betodata[(vs, ve)] = data[f]
        polys = []
        poly_data = []
        while boundary_edges:
            e = boundary_edges.pop()
            ((vstart, ve), face_i) = edges[e]
            poly = [vstart, ve]
            datum = betodata[(vstart, ve)]
            while ve != vstart:
                if ve not in vstobe:
                    print("whoops, couldn't close boundary")
                    break
                nextes = vstobe[ve]
                if len(nextes) == 1:
                    nexte = nextes[0]
                else:
                    # find a next edge with face index face_i
                    # TODO: this is not guaranteed to work,
                    # as continuation edge may have been for a different
                    # face that is now combined with face_i by erasing
                    # interior edges. Find a better algorithm here.
                    nexte = -1
                    for ne_cand in nextes:
                        if edges[ne_cand][1] == face_i:
                            nexte = ne_cand
                            break
                    if nexte == -1:
                        # case mentioned in TODO may have happened;
                        # just choose any nexte - may mess things up
                        nexte = nextes[0]
                ((_, ve), face_i) = edges[nexte]
                if nexte not in boundary_edges:
                    print("whoops, nexte not a boundary edge", nexte)
                    break
                boundary_edges.remove(nexte)
                if ve != vstart:
                    poly.append(ve)
            polys.append(poly)
            poly_data.append(datum)
        if len(polys) == 0:
            # can happen if an entire closed polytope is given
            # at least until we do an edge check
            return []
        elif len(polys) == 1:
            ans.append(PolyArea(points, polys[0], [], poly_data[0]))
        else:
            outerf = _FindOuterPoly(polys, points, faces)
            pa = PolyArea(points, polys[outerf], [], poly_data[outerf])
            pa.holes = [polys[i] for i in range(len(polys)) if i != outerf]
            ans.append(pa)
    return ans


def _GetEdgeData(faces):
    """Find edges from faces, and some lookup dictionaries.

    Args:
      faces: list of list of int - each a closed CCW polygon of vertex indices
    Returns:
      (list of ((int, int), int), dict{ int->list of int}) -
        list elements are ((startv, endv), face index)
        dict maps vertices to edge indices
    """

    edges = []
    vtoe = dict()
    for findex, f in enumerate(faces):
        nf = len(f)
        for i, v in enumerate(f):
            endv = f[(i + 1) % nf]
            edges.append(((v, endv), findex))
            eindex = len(edges) - 1
            if v in vtoe:
                vtoe[v].append(eindex)
            else:
                vtoe[v] = [eindex]
    return (edges, vtoe)


def _GetFaceGraph(faces, edges, vtoe, points):
    """Find the face adjacency graph.

    Faces are adjacent if they share an edge,
    and the shared edge goes in the reverse direction,
    and if the angle between them isn't too large.

    Args:
      faces: list of list of int
      edges: list of ((int, int), int) - see _GetEdgeData
      vtoe: dict{ int->list of int } - see _GetEdgeData
      points: geom.Points
    Returns:
      (list of  list of int, list of bool) -
        first list: each sublist is adjacent face indices for each face
        second list: maps edge index to True if it separates adjacent faces
    """

    face_adj = [[] for i in range(len(faces))]
    is_interior_edge = [False] * len(edges)
    for e, ((vs, ve), f) in enumerate(edges):
        for othere in vtoe[ve]:
            ((_, we), g) = edges[othere]
            if we == vs:
                # face g is adjacent to face f
                # TODO: angle check
                if g not in face_adj[f]:
                    face_adj[f].append(g)
                    is_interior_edge[e] = True
                # Don't bother with mirror relations, will catch later
    return (face_adj, is_interior_edge)


def _FindFaceGraphComponents(faces, face_adj):
    """Partition faces into connected components.

    Args:
      faces: list of list of int
      face_adj: list of list of int - see _GetFaceGraph
    Returns:
      (list of list of int, list of int) -
        first list partitions face indices into separate lists,
            each a component
        second list maps face indices into their component index
    """

    if not faces:
        return ([], [])
    components = []
    ftoc = [-1] * len(faces)
    for i in range(len(faces)):
        if ftoc[i] == -1:
            compi = len(components)
            comp = []
            _FFGCSearch(i, faces, face_adj, ftoc, compi, comp)
            components.append(comp)
    return (components, ftoc)


def _FFGCSearch(findex, faces, face_adj, ftoc, compi, comp):
    """Depth first search helper function for _FindFaceGraphComponents

    Searches recursively through all faces connected to findex, adding
    each face found to comp and setting ftoc for that face to compi.
    """

    comp.append(findex)
    ftoc[findex] = compi
    for otherf in face_adj[findex]:
        if ftoc[otherf] == -1:
            _FFGCSearch(otherf, faces, face_adj, ftoc, compi, comp)


def _FindOuterPoly(polys, points, faces):
    """Assuming polys has one CCW-oriented face when looking
    down average normal of faces, return that one.

    Only one of the faces should have a normal whose dot product
    with the average normal of faces is positive.

    Args:
      polys: list of list of int - list of polys given by vertex indices
      points: geom.Points
      faces: list of list of int - original selected region, used to find
          average normal
    Returns:
      int - the index in polys of the outermost one
    """

    if len(polys) < 2:
        return 0
    fnorm = (0.0, 0.0, 0.0)
    for face in faces:
        if len(face) > 2:
            fnorm = VecAdd(fnorm, Newell(face, points))
    if fnorm == (0.0, 0.0, 0.0):
        return 0
    # fnorm is really a multiple of the normal, but fine for test below
    for i, poly in enumerate(polys):
        if len(poly) > 2:
            pnorm = Newell(poly, points)
            if VecDot(fnorm, pnorm) > 0:
                return i
    print("whoops, couldn't find an outermost poly")
    return 0


def _RotatedPolyAreaToXY(polyarea, norm):
    """Return a  PolyArea rotated to xy plane.

    Only the points in polyarea will be transferred.

    Args:
      polyarea: geom.PolyArea
      norm: the normal for polyarea
    Returns:
      (geom.PolyArea, (float, ..., float), dict{ int -> int }) - new PolyArea,
          4x3 inverse transform, dict mapping new verts to old ones
    """

    # find rotation matrix that takes norm to (0,0,1)
    (nx, ny, nz) = norm
    if abs(nx) < abs(ny) and abs(nx) < abs(nz):
        v = (vx, vy, vz) = Norm3(0.0, nz, - ny)
    elif abs(ny) < abs(nz):
        v = (vx, vy, vz) = Norm3(nz, 0.0, - nx)
    else:
        v = (vx, vy, vz) = Norm3(ny, - nx, 0.0)
    (ux, uy, uz) = Cross3(v, norm)
    rotmat = [ux, vx, nx, uy, vy, ny, uz, vz, nz, 0.0, 0.0, 0.0]
    # rotation matrices are orthogonal, so inverse is transpose
    invrotmat = [ux, uy, uz, vx, vy, vz, nx, ny, nz, 0.0, 0.0, 0.0]
    pointmap = dict()
    invpointmap = dict()
    newpoints = Points()
    for poly in [polyarea.poly] + polyarea.holes:
        for v in poly:
            vcoords = polyarea.points.pos[v]
            newvcoords = MulPoint3(vcoords, rotmat)
            newv = newpoints.AddPoint(newvcoords)
            pointmap[v] = newv
            invpointmap[newv] = v
    pa = PolyArea(newpoints)
    pa.poly = [pointmap[v] for v in polyarea.poly]
    pa.holes = [[pointmap[v] for v in hole] for hole in polyarea.holes]
    pa.data = polyarea.data
    return (pa, invrotmat, invpointmap)


def _AddTransformedPolysToModel(mdl, polys, points, poly_data,
                                transform, pointmap):
    """Add (transformed) the points and faces to a model.

    Add polys to mdl.  The polys have coordinates given by indices
    into points.pos; those need to be transformed by multiplying by
    the transform matrix.
    The vertices may already exist in mdl.  Rather than relying on
    AddPoint to detect the duplicate (transform rounding error makes
    that dicey), the pointmap dictionar is used to map vertex indices
    in polys into those in mdl - if they exist already.

    Args:
      mdl: geom.Model - where to put new vertices, faces
      polys: list of list of int - each sublist a poly
      points: geom.Points - coords for vertices in polys
      poly_data: list of any - parallel to polys
      transform: (float, ..., float) - 12-tuple, a 4x3 transform matrix
      pointmap: dict { int -> int } - maps new vertex indices to old ones
    Side Effects:
      The model gets new faces and vertices, based on those in polys.
      We are allowed to modify pointmap, as it will be discarded after call.
    """

    for i, coords in enumerate(points.pos):
        if i not in pointmap:
            p = MulPoint3(coords, transform)
            pointmap[i] = mdl.points.AddPoint(p)
    for i, poly in enumerate(polys):
        mpoly = [pointmap[v] for v in poly]
        mdl.faces.append(mpoly)
        mdl.face_data.append(poly_data[i])


# ====================================================================================
#       DRIVER FUNCTION
# ====================================================================================
import bmesh


def inset_polygon(mesh, amount, height, region, as_percent):
    if amount <= 0.0:
        return
    pitch = math.atan(height / amount)
    selfaces = []
    selface_indices = []
    bm = bmesh.from_edit_mesh(mesh)
    for face in bm.faces:
        if face.select:
            selfaces.append(face)
            selface_indices.append(face.index)
    m = Model()
    # if add all mesh.vertices, coord indices will line up
    # Note: not using Points.AddPoint which does dup elim
    # because then would have to map vertices in and out
    m.points.pos = [v.co.to_tuple() for v in bm.verts]
    for f in selfaces:
        m.faces.append([loop.vert.index for loop in f.loops])
        m.face_data.append(f.index)
    orig_numv = len(m.points.pos)
    orig_numf = len(m.faces)
    BevelSelectionInModel(m, amount, pitch, True, region, as_percent)
    if len(m.faces) == orig_numf:
        # something went wrong with Bevel - just treat as no-op
        return
    blender_faces = m.faces[orig_numf:len(m.faces)]
    blender_old_face_index = m.face_data[orig_numf:len(m.faces)]
    for i in range(orig_numv, len(m.points.pos)):
        bvertnew = bm.verts.new(m.points.pos[i])
    bm.verts.index_update()
    new_faces = []
    start_faces = len(bm.faces)
    for i, newf in enumerate(blender_faces):
        bm.verts.ensure_lookup_table()
        bm.faces.ensure_lookup_table()

        vs = [bm.verts[j] for j in newf]
        # copy face attributes from old face that it was derived from
        bfi = blender_old_face_index[i]
        if bfi and 0 <= bfi < start_faces:
            oldface = bm.faces[bfi]
            bfacenew = bm.faces.new(vs, oldface)
            # bfacenew.copy_from_face_interp(oldface)
        else:
            bfacenew = bm.faces.new(vs)
    # remove original faces
    for face in selfaces:
        face.select_set(False)
        bm.faces.remove(face)
    bm.faces.index_update()
    # mesh.update(calc_edges=True)
    # select all new faces
    for face in new_faces:
        face.select_set(True)
