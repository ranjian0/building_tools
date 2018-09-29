import bpy
import bmesh
import math

from mathutils import Vector
from bmesh.types import BMVert, BMEdge, BMFace
from ...utils import (
    select,
    skeletonize,
    filter_geom,
    calc_edge_median,
    calc_verts_median,
    filter_vertical_edges,
    filter_horizontal_edges
    )

def make_roof(bm, faces, type, **kwargs):
    select(faces, False)
    if type == 'FLAT':
        make_flat_roof(bm, faces, **kwargs)
    elif type == 'GABLE':
        make_gable_roof(bm, faces, **kwargs)
    elif type == 'HIP':
        make_hip_roof(bm, faces, **kwargs)

def make_flat_roof(bm, faces, thick, outset, **kwargs):

    ret = bmesh.ops.extrude_face_region(bm, geom=faces)
    bmesh.ops.translate(bm,
        vec=(0, 0, thick),
        verts=filter_geom(ret['geom'], BMVert))

    top_face = filter_geom(ret['geom'], BMFace)[-1]
    link_faces = [f for e in top_face.edges for f in e.link_faces
                    if f is not top_face]

    bmesh.ops.inset_region(bm, faces=link_faces, depth=outset, use_even_offset=True)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)

    bmesh.ops.delete(bm,
        geom=faces,
        context=5)

def make_gable_roof(bm, faces, thick, outset, height, orient, **kwargs):
    if not is_rectangular(faces):
        return

    # -- if more than one face, dissolve
    if len(faces) > 1:
        faces = bmesh.ops.dissolve_faces(bm,
            faces=faces, use_verts=True).get('region')

    # -- extrude the face to height
    ret = bmesh.ops.extrude_face_region(bm, geom=faces)
    verts = filter_geom(ret['geom'], BMVert)
    edges = filter_geom(ret['geom'], BMEdge)
    nfaces = filter_geom(ret['geom'], BMFace)
    bmesh.ops.translate(bm, verts=verts, vec=(0, 0, height))
    bmesh.ops.delete(bm, geom=faces + nfaces, context=3)

    # -- merge opposite verts
    axis = 'x' if orient == 'LEFT' else 'y'
    _max = max([v for e in edges for v in e.verts], key=lambda v: getattr(v.co, axis))
    _min = min([v for e in edges for v in e.verts], key=lambda v: getattr(v.co, axis))
    mid = getattr((_max.co + _min.co)/2, axis)
    for v in set([v for e in edges for v in e.verts]):
        setattr(v.co, axis, mid)
    bmesh.ops.remove_doubles(bm, verts=bm.verts)

    # -- offset roof boundary
    maxz = max([v.co.z for v in bm.verts])
    top_verts = [v for v in bm.verts if v.co.z == maxz]
    faces = list(set([f for v in top_verts for f in v.link_faces if f.normal.z]))
    boundary_edges = [e for f in faces for e in f.edges
        if len(set(e.link_faces) - set(faces)) == 1]
    bmesh.ops.delete(bm, geom=faces, context=5)

    ret = bmesh.ops.extrude_edge_only(bm, edges=boundary_edges)
    verts = filter_geom(ret['geom'], BMVert)
    bmesh.ops.scale(bm, verts=verts, vec=(1 + outset, 1 + outset, 1))
    nedges = list(set([e for v in verts for e in v.link_edges if e.is_boundary]))

    # -- fix roof slope at bottom edges
    min_edges = [e for e in nedges
        if calc_edge_median(e).z == min([v.co.z for e in nedges for v in e.verts])]
    bmesh.ops.translate(bm,
        verts=list(set([v for e in min_edges for v in e.verts])),
        vec=(0, 0, -outset))

    # -- extrude edges upwards and fill face
    ret = bmesh.ops.extrude_edge_only(bm, edges=nedges)
    verts = filter_geom(ret['geom'], BMVert)
    edges = filter_geom(ret['geom'], BMEdge)
    bmesh.ops.translate(bm, verts=verts, vec=(0, 0, thick))

    valid_edges = [e for e in edges
        if calc_edge_median(e).z != min([v.co.z for e in edges for v in e.verts])]
    edge_loc = set([getattr(calc_edge_median(e), axis) for e in valid_edges])

    # -- fill faces
    for loc in edge_loc:
        edges = [e for e in valid_edges if getattr(calc_edge_median(e), axis) == loc]
        bmesh.ops.contextual_create(bm, geom=edges)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)

def make_hip_roof(bm, faces, **kwargs):
    # -- if more than one face, dissolve
    if len(faces) > 1:
        faces = bmesh.ops.dissolve_faces(bm,
            faces=faces, use_verts=True).get('region')
    face = faces[-1]
    convex = all([loop.is_convex for loop in face.loops])

    # get verts in anti-clockwise order
    center = face.calc_center_median().to_tuple()[:2]
    verts = [v.co.to_tuple()[:2] for v in face.verts]
    verts.sort(key=lambda v:clockwise(v, center), reverse=True)

    # compute skeleton
    skeleton = skeletonize(verts, [])
    print(skeleton)

def is_rectangular(faces):
    # -- determine if faces form a rectangular area
    face_area = sum([f.calc_area() for f in faces])

    verts = [v for f in faces for v in f.verts]
    verts = sorted(verts, key=lambda v: (v.co.x, v.co.y))

    _min, _max = verts[0], verts[-1]
    width = abs(_min.co.x - _max.co.x)
    length = abs(_min.co.y - _max.co.y)
    area = width * length

    if round(face_area, 4) == round(area, 4):
        return True
    return False

def clockwise(point, origin=(0, 0)):
    # https://stackoverflow.com/questions/41855695/sorting-list-of-two-dimensional-coordinates-by-clockwise-angle-using-python
    refvec = [0, 1] # y-axis

    # Vector between point and the origin: v = p - o
    vector = [point[0]-origin[0], point[1]-origin[1]]
    # Length of vector: ||v||
    lenvector = math.hypot(vector[0], vector[1])
    # If length is zero there is no angle
    if lenvector == 0:
        return -math.pi, 0
    # Normalize vector: v/||v||
    normalized = [vector[0]/lenvector, vector[1]/lenvector]
    dotprod  = normalized[0]*refvec[0] + normalized[1]*refvec[1]     # x1*x2 + y1*y2
    diffprod = refvec[1]*normalized[0] - refvec[0]*normalized[1]     # x1*y2 - y1*x2
    angle = math.atan2(diffprod, dotprod)
    # Negative angles represent counter-clockwise angles so we need to subtract them
    # from 2*pi (360 degrees)
    if angle < 0:
        return 2*math.pi+angle, lenvector
    # I return first the angle because that's the primary sorting criterium
    # but if two vectors have the same angle then the shorter distance should come first.
    return angle, lenvector