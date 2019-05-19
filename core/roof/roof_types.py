import math
import bmesh
import operator
from mathutils import Vector
from bmesh.types import BMVert, BMEdge, BMFace
from ...utils import equal, select, skeletonize, filter_geom, calc_edge_median


def make_roof(bm, faces, prop):
    """Create different roof types

    Args:
        bm (bmesh.types.BMesh): bmesh from current edit mesh
        faces (bmesh.types.BMFace): list of user selected faces
        type (str): type of roof to generate as defined in RoofProperty
        **kwargs: Extra kargs from RoofProperty
    """

    select(faces, False)
    if prop.type == "FLAT":
        make_flat_roof(bm, faces, prop)
    elif prop.type == "GABLE":
        make_gable_roof(bm, faces, prop)
    elif prop.type == "HIP":
        make_hip_roof(bm, faces, prop)


def make_flat_roof(bm, faces, prop):
    """Create a basic flat roof

    Args:
        bm (bmesh.types.BMesh): bmesh from current edit mesh
        faces (bmesh.types.BMFace): list of user selected faces

    Returns:
        list(bmesh.types.BMFace): Resulting top face
    """
    ret = bmesh.ops.extrude_face_region(bm, geom=faces)
    bmesh.ops.translate(
        bm, vec=(0, 0, prop.thickness), verts=filter_geom(ret["geom"], BMVert)
    )

    top_face = filter_geom(ret["geom"], BMFace)[-1]
    link_faces = [f for e in top_face.edges for f in e.link_faces if f is not top_face]

    bmesh.ops.inset_region(
        bm, faces=link_faces, depth=prop.outset, use_even_offset=True
    )
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bmesh.ops.delete(bm, geom=faces, context="FACES")

    new_faces = list({f for e in top_face.edges for f in e.link_faces})
    return bmesh.ops.dissolve_faces(bm, faces=new_faces).get("region")


def make_gable_roof(bm, faces, prop):
    """Create a gable roof

    Args:
        bm (bmesh.types.BMesh): bmesh from current edit mesh
        faces (bmesh.types.BMFace): list of user selected faces
    """
    if not is_rectangular(faces):
        return

    axis = "x" if prop.orient == "HORIZONTAL" else "y"
    if len(faces) > 1:
        faces = bmesh.ops.dissolve_faces(bm, faces=faces, use_verts=True).get("region")

    edges = extrude_up_and_delete_faces(bm, faces, prop.height)
    merge_verts_along_axis(bm, set(v for e in edges for v in e.verts), axis)

    roof_faces = get_highest_z_facing_faces(bm)
    boundary_edges = [
        e for f in roof_faces for e in f.edges if e.calc_face_angle(1000.0) < math.pi
    ]
    bmesh.ops.delete(bm, geom=roof_faces, context="FACES")

    hang_edges = create_roof_hangs(bm, boundary_edges, prop.outset)
    fill_roof_faces_from_hang(bm, hang_edges, prop.thickness, axis)


def make_hip_roof(bm, faces, prop):
    """Create a hip roof

    Args:
        bm (bmesh.types.BMesh): bmesh from current edit mesh
        faces (bmesh.types.BMFace): list of user selected faces
    """

    DEPRECATED_hip_roof(bm, faces, prop)


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

    start_loop = max(face.loops, key=lambda loop: loop.vert.co.to_tuple()[:2])

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


def extrude_up_and_delete_faces(bm, faces, extrude_depth):
    ret = bmesh.ops.extrude_face_region(bm, geom=faces)
    verts = filter_geom(ret["geom"], BMVert)
    edges = filter_geom(ret["geom"], BMEdge)
    nfaces = filter_geom(ret["geom"], BMFace)
    bmesh.ops.translate(bm, verts=verts, vec=(0, 0, extrude_depth))
    bmesh.ops.delete(bm, geom=faces + nfaces, context="FACES_ONLY")
    return edges


def merge_verts_along_axis(bm, verts, axis):
    key_func = operator.attrgetter("co." + axis)
    _max = max(verts, key=key_func)
    _min = min(verts, key=key_func)
    mid = getattr((_max.co + _min.co) / 2, axis)
    for v in verts:
        setattr(v.co, axis, mid)
    bmesh.ops.remove_doubles(bm, verts=bm.verts)


def get_highest_z_facing_faces(bm):
    maxz = max([v.co.z for v in bm.verts])
    top_verts = [v for v in bm.verts if v.co.z == maxz]
    return list(set([f for v in top_verts for f in v.link_faces if f.normal.z]))


def create_roof_hangs(bm, edges, size):
    ret = bmesh.ops.extrude_edge_only(bm, edges=edges)
    verts = filter_geom(ret["geom"], BMVert)
    bmesh.ops.scale(bm, verts=verts, vec=(1 + size, 1 + size, 1))
    hang_edges = list(
        {e for v in verts for e in v.link_edges if all([v in verts for v in e.verts])}
    )

    # -- fix roof slope at bottom edges
    min_loc_z = min([v.co.z for e in hang_edges for v in e.verts])
    min_verts = list({v for e in hang_edges for v in e.verts if v.co.z == min_loc_z})
    bmesh.ops.translate(bm, verts=min_verts, vec=(0, 0, -size))
    return hang_edges


def fill_roof_faces_from_hang(bm, edges, roof_thickness, axis):
    # -- extrude edges upwards and fill face
    ret = bmesh.ops.extrude_edge_only(bm, edges=edges)
    verts = filter_geom(ret["geom"], BMVert)
    edges = filter_geom(ret["geom"], BMEdge)
    bmesh.ops.translate(bm, verts=verts, vec=(0, 0, roof_thickness))

    valid_edges = [
        e
        for e in edges
        if calc_edge_median(e).z != min([v.co.z for e in edges for v in e.verts])
    ]
    edge_loc = set([getattr(calc_edge_median(e), axis) for e in valid_edges])

    # -- fill faces
    for loc in edge_loc:
        edges = [e for e in valid_edges if getattr(calc_edge_median(e), axis) == loc]
        bmesh.ops.contextual_create(bm, geom=edges)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)


def create_hip_edges_and_verts(bm, skeleton, height_scale, median):

    skeleton_edges = []
    for arc in skeleton:
        source = arc.source
        vsource = vert_at_loc(source, bm.verts)
        if not vsource:
            ht = (
                height_scale
                * [arc.height for arc in skeleton if arc.source == source][-1]
            )
            vsource = bmesh.ops.create_vert(
                bm, co=Vector((source.x, source.y, median.z + ht))
            ).get("vert")[-1]

        for sink in arc.sinks:
            # -- create sink vert
            vs = vert_at_loc(sink, bm.verts)
            if not vs:
                ht = height_scale * min(
                    [arc.height for arc in skeleton if sink in arc.sinks]
                )
                vs = bmesh.ops.create_vert(
                    bm, co=Vector((sink.x, sink.y, median.z + ht))
                ).get("vert")[-1]

            # create edge
            if vs != vsource:
                geom = bmesh.ops.contextual_create(bm, geom=[vsource, vs]).get("edges")
                skeleton_edges.extend(geom)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0001)
    return skeleton_edges


def create_hip_faces(bm, original_edges, skeleton_edges):
    for ed in original_edges:
        # -- determine skeleton_edges linked to this original edge
        linked_skeleton_edges = [e
                                 for v in ed.verts
                                 for e in set(v.link_edges).intersection(skeleton_edges)]

        if len(linked_skeleton_edges) == 2:
            cycle_edges_make_polygon(bm, ed, skeleton_edges)

        # elif len(face_edges) == 1:
        #     # -- special case
        #     # -- means that original edge has a lone vert(not connected to skeleton)

        #     # -- cycle edge links only once
        #     fedge = face_edges[-1]
        #     common_vert = [v for v in ed.verts if v in fedge.verts][-1]

        #     start = fedge.other_vert(common_vert)
        #     end = ed.other_vert(common_vert)

        #     closest = None
        #     distance = 1000
        #     for ledge in start.link_edges:
        #         if ledge != fedge:
        #             next_vert = ledge.other_vert(start)
        #             new_dist = (next_vert.co - end.co).length
        #             if new_dist < distance:
        #                 closest = next_vert
        #                 distance = new_dist
        #     new_edge = bm.edges.get([closest, start])
        #     face_edges.append(new_edge)
        #     face_edges.append(ed)

        # bmesh.ops.contextual_create(bm, geom=face_edges)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0001)


def DP_cycle_edges_make_polygon(bm, original_edge, skeleton_edges):
    start, end = original_edge.verts

    valid_start_edges = [e for e in start.link_edges if e in skeleton_edges]
    valid_end_edges = [e for e in end.link_edges if e in skeleton_edges]

    if len(valid_end_edges) == 1 and len(valid_start_edges) == 1:
        start_e, end_e = valid_start_edges[-1], valid_end_edges[-1]

        # if edges have common vert, we have a triange
        if len(set(list(start_e.verts) + list(end_e.verts))) == 3:
            bmesh.ops.contextual_create(bm,
                                        geom=[original_edge, start_e, end_e])
        else:

            # if other verts form and edge, we have a quad
            other_vert_start = start_e.other_vert(start)
            other_vert_end = end_e.other_vert(end)
            edge = bm.edges.get([other_vert_start, other_vert_end], None)
            if edge is not None:
                bmesh.ops.contextual_create(bm,
                                            geom=[original_edge, start_e, end_e, edge])


def cycle_edges_make_polygon(bm, original_edge, skeleton_edges):
    start, end = sorted(original_edge.verts, key=lambda v: v.co.x)

    current_vert = start
    processed_verts = set([start])
    processed_edges = [original_edge]
    while True:
        # -- find closest vert
        valid_edges = [e for e in current_vert.link_edges
                       if e in skeleton_edges and e not in processed_edges]
        if not valid_edges:
            break

        closest, e = find_closest_vert_in_edges(current_vert, end, valid_edges)
        if closest == end:
            break

        processed_verts.add(closest)
        processed_edges.append(e)
        current_vert = closest

    processed_verts.add(end)
    bmesh.ops.contextual_create(bm, geom=list(processed_verts))


def find_closest_vert_in_edges(current_vert, compare_vert, edges):
    closest = None
    distance = 1000.0
    current_edge = None
    for e in edges:
        current_edge = e
        other_vert = e.other_vert(current_vert)
        if other_vert == compare_vert:
            return other_vert, current_edge

        dist = (compare_vert.co - current_vert.co).length
        if dist < distance:
            closest = other_vert
            distance = dist
    return closest, current_edge


def DEPRECATED_hip_roof(bm, faces, prop):

    faces = make_flat_roof(bm, faces, prop)
    face = faces[-1]
    median = face.calc_center_median()

    # get verts in anti-clockwise order
    original_edges = [e for e in face.edges]
    verts = [v for v in sort_verts_by_loops(face)]
    points = [v.co.to_tuple()[:2] for v in verts]

    # compute skeleton
    skeleton = skeletonize(points, [])
    bmesh.ops.delete(bm, geom=faces, context="FACES_ONLY")

    height_scale = prop.height / max([arc.height for arc in skeleton])

    # 3. -- create edges and vertices
    skeleton_edges = []
    for arc in skeleton:
        source = arc.source
        vsource = vert_at_loc(source, bm.verts)
        if not vsource:
            ht = (
                height_scale
                * [arc.height for arc in skeleton if arc.source == source][-1]
            )
            vsource = bmesh.ops.create_vert(
                bm, co=Vector((source.x, source.y, median.z + ht))
            ).get("vert")[-1]

        for sink in arc.sinks:
            # -- create sink vert
            vs = vert_at_loc(sink, bm.verts)
            if not vs:
                ht = height_scale * min(
                    [arc.height for arc in skeleton if sink in arc.sinks]
                )
                vs = bmesh.ops.create_vert(
                    bm, co=Vector((sink.x, sink.y, median.z + ht))
                ).get("vert")[-1]

            # create edge
            if vs != vsource:
                geom = bmesh.ops.contextual_create(bm, geom=[vsource, vs]).get("edges")
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
                for e in current_vert.link_edges:
                    if e not in skeleton_edges or e in processed_edges:
                        continue

                    other_vert = e.other_vert(current_vert)

                    dist = (other_vert.co - end.co).length
                    if dist < distance:
                        closest = other_vert
                        distance = dist

                # -- add edge between closest and current if any
                if closest == current_vert:
                    break
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
                    if new_dist < distance:
                        closest = next_vert
                        distance = new_dist
            new_edge = bm.edges.get([closest, start])
            face_edges.append(new_edge)
            face_edges.append(ed)

            bmesh.ops.contextual_create(bm, geom=face_edges)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0001)
