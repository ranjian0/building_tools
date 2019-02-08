import bpy
import math
import bmesh
import itertools as it

from mathutils import Vector
from bmesh.types import BMVert, BMEdge, BMFace
from ...utils import (
    equal,
    select,
    skeletonize,
    filter_geom,
    calc_edge_median,
    calc_verts_median,
    filter_vertical_edges,
    filter_horizontal_edges
    )

def make_roof(bm, faces, type, **kwargs):
    """Create different roof types

    Args:
        bm (bmesh.types.BMesh): bmesh from current edit mesh
        faces (bmesh.types.BMFace): list of user selected faces
        type (str): type of roof to generate as defined in RoofProperty
        **kwargs: Extra kargs from RoofProperty
    """

    select(faces, False)
    if type == 'FLAT':
        make_flat_roof(bm, faces, **kwargs)
    elif type == 'GABLE':
        make_gable_roof(bm, faces, **kwargs)
    elif type == 'HIP':
        make_hip_roof(bm, faces, **kwargs)

def make_flat_roof(bm, faces, thick, outset, **kwargs):
    """Create a basic flat roof

    Args:
        bm (bmesh.types.BMesh): bmesh from current edit mesh
        faces (bmesh.types.BMFace): list of user selected faces
        thick (float): Thickness of the roof
        outset (float): How mush the roof overhangs
        **kwargs: Extra kargs from RoofProperty

    Returns:
        list(bmesh.types.BMFace): Resulting top face
    """
    ret = bmesh.ops.extrude_face_region(bm, geom=faces)
    bmesh.ops.translate(bm,
        vec=(0, 0, thick),
        verts=filter_geom(ret['geom'], BMVert))

    top_face = filter_geom(ret['geom'], BMFace)[-1]
    link_faces = [f for e in top_face.edges for f in e.link_faces
                    if f is not top_face]

    bmesh.ops.inset_region(bm, faces=link_faces, depth=outset, use_even_offset=True)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bmesh.ops.delete(bm, geom=faces, context=5)

    new_faces = list({f for e in top_face.edges for f in e.link_faces})
    return bmesh.ops.dissolve_faces(bm, faces=new_faces).get('region')

def make_gable_roof(bm, faces, thick, outset, height, orient, **kwargs):
    """Create a gable roof

    Args:
        bm (bmesh.types.BMesh): bmesh from current edit mesh
        faces (bmesh.types.BMFace): list of user selected faces
        thick (float): Thickness of the roof
        outset (float): How mush the roof overhangs
        height (float): Height of the roof overhangs
        orient (str): Orientation/rotation for the roof (left or right)
        **kwargs: Extra kargs from RoofProperty
    """

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
    nedges = list(set([e for v in verts for e in v.link_edges
                        if all([v in verts for v in e.verts])]))

    # -- fix roof slope at bottom edges
    min_loc_z = min([v.co.z for e in nedges for v in e.verts])
    min_verts = list({v for e in nedges for v in e.verts if v.co.z == min_loc_z})
    bmesh.ops.translate(bm,
        verts=min_verts, vec=(0, 0, -outset))

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

def make_hip_roof(bm, faces, thick, outset, height, **kwargs):
    """Create a hip roof

    Args:
        bm (bmesh.types.BMesh): bmesh from current edit mesh
        faces (bmesh.types.BMFace): list of user selected faces
        thick (float): Thickness of the roof
        outset (float): How mush the roof overhangs
        height (float): Height of the roof overhangs
        **kwargs: Extra kargs from RoofProperty
    """


    faces = make_flat_roof(bm, faces, thick, outset, **kwargs)
    face = faces[-1]
    median = face.calc_center_median()

    # get verts in anti-clockwise order
    original_edges = [e for e in face.edges]
    verts = [v for v in sort_verts_by_loops(face)]
    points = [v.co.to_tuple()[:2] for v in verts]

    # compute skeleton
    skeleton = skeletonize(points, [])

    # create hip roof from skeleton
    # 1. -- remove face
    bmesh.ops.delete(bm, geom=faces, context=3)

    # 2. -- determine height scale for skeleton
    height_scale = height/max([arc.height for arc in skeleton])

    # 3. -- create edges and vertices
    skeleton_edges = []
    for arc in skeleton:
        source = arc.source
        vsource = vert_at_loc(source, bm.verts)
        if not vsource:
            ht = height_scale * [arc.height for arc in skeleton if arc.source == source][-1]
            vsource = bmesh.ops.create_vert(bm,
                        co=Vector((source.x, source.y, median.z + ht))).get('vert')[-1]

        for sink in arc.sinks:
            # -- create sink vert
            vs = vert_at_loc(sink, bm.verts)
            if not vs:
                ht = height_scale * min([arc.height for arc in skeleton if sink in arc.sinks])
                vs = bmesh.ops.create_vert(bm,
                        co=Vector((sink.x, sink.y, median.z + ht))).get('vert')[-1]

            # create edge
            if vs != vsource:
                geom = bmesh.ops.contextual_create(bm, geom=[vsource, vs]).get('edges')
                skeleton_edges.extend(geom)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0001)

    # 4. -- create faces
    for ed in original_edges:

        # -- determine skeleton_edges linked to this original edge
        face_edges = []
        for v in ed.verts:
            common = set(v.link_edges).intersection(skeleton_edges)
            face_edges.extend(list(common))

        if len(face_edges) == 2:
        # -- cycle through edge links until we form a polygon
            processed_edges = [ed]
            start, end = ed.verts

            closest = None
            current_vert = start
            while current_vert != end:
                distance = 1000
                # -- find new closest vert
                for e in current_vert.link_edges :
                    if e not in skeleton_edges or e in processed_edges: continue

                    other_vert = e.other_vert(current_vert)

                    dist = (other_vert.co - end.co).length
                    if dist < distance:
                        closest = other_vert
                        distance = dist

                # -- add edge between closest and current if any
                if closest == current_vert: break
                new_edge = bm.edges.get([closest, current_vert])
                if new_edge:
                    processed_edges.append(new_edge)

                # -- update current
                current_vert = closest

            bmesh.ops.contextual_create(bm, geom=processed_edges)
        elif len(face_edges) == 1:
        # -- special case
        # -- means that original edge has a lone vert(not connected to skeleton)

        # -- cycle edge links only once
            fedge = face_edges[-1]
            common_vert = [v for v in ed.verts if v in fedge.verts][-1]

            start = fedge.other_vert(common_vert)
            end = ed.other_vert(common_vert)

            closest = None
            distance = 1000
            for ledge in start.link_edges:
                if ledge != fedge:
                    next_vert = ledge.other_vert(start)
                    new_dist = (next_vert.co - end.co).length
                    if new_dist  < distance:
                        closest = next_vert
                        distance = new_dist
            new_edge = bm.edges.get([closest, start])
            face_edges.append(new_edge)
            face_edges.append(ed)

            bmesh.ops.contextual_create(bm, geom=face_edges)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0001)


def is_rectangular(faces):
    """ Determine if faces form a recatngular area """

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

def sort_verts_by_loops(face):
    """ sort verts in face clockwise using loops """

    start_loop = max(face.loops,
        key=lambda loop: loop.vert.co.to_tuple()[:2])

    verts = []
    current_loop = start_loop
    while len(verts) < len(face.loops):
        verts.append(current_loop.vert)
        current_loop = current_loop.link_loop_prev

    return verts

def vert_at_loc(loc, verts, loc_z=None):
    """ Find all verts at loc(x,y), return the one with highest z coord """

    results = []
    for vert in verts:
        co = vert.co
        if equal(co.x, loc.x) and equal(co.y, loc.y):
            if loc_z:
                if equal(co.z, loc_z):
                    results.append(vert)
            else:
                results.append(vert)

    if results:
        return max([v for v in results], key=lambda v: v.co.z)
    return None
