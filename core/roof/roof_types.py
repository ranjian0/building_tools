import bmesh
import operator
import mathutils
from mathutils import Vector
from bmesh.types import BMVert, BMEdge, BMFace
from ...utils import (
    equal,
    select,
    FaceMap,
    validate,
    skeletonize,
    filter_geom,
    map_new_faces,
    calc_edge_median,
    add_faces_to_map,
    add_facemap_for_groups,
)


def create_roof(bm, faces, prop):
    """Create roof types
    """
    select(faces, False)
    if prop.type == "FLAT":
        create_flat_roof(bm, faces, prop)
    elif prop.type == "GABLE":
        add_facemap_for_groups(FaceMap.ROOF_HANGS)
        create_gable_roof(bm, faces, prop)
    elif prop.type == "HIP":
        add_facemap_for_groups(FaceMap.ROOF_HANGS)
        create_hip_roof(bm, faces, prop)


@map_new_faces(FaceMap.ROOF)
def create_flat_roof(bm, faces, prop):
    """Create a flat roof
    """
    ret = bmesh.ops.extrude_face_region(bm, geom=faces)
    bmesh.ops.translate(
        bm, vec=(0, 0, prop.thickness), verts=filter_geom(ret["geom"], BMVert)
    )
    top_face = filter_geom(ret["geom"], BMFace)
    if len(top_face) > 1:
        top_face = bmesh.ops.dissolve_faces(
            bm, faces=top_face, use_verts=True).get("region").pop()
    else:
        top_face = top_face.pop()

    link_faces = [f for e in top_face.edges for f in e.link_faces if f is not top_face]

    bmesh.ops.inset_region(
        bm, faces=link_faces, depth=prop.outset, use_even_offset=True
    )
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bmesh.ops.delete(bm, geom=faces, context="FACES")

    new_faces = list({f for e in top_face.edges for f in e.link_faces})
    return bmesh.ops.dissolve_faces(bm, faces=new_faces).get("region")


def create_gable_roof(bm, faces, prop):
    """Create a gable roof
    """
    if not is_rectangular(faces):
        return

    if len(faces) > 1:
        faces = bmesh.ops.dissolve_faces(bm, faces=faces, use_verts=True).get("region")

    axis = "x" if prop.orient == "HORIZONTAL" else "y"
    edges = extrude_up_and_delete_faces(bm, faces, prop.height)
    merge_verts_along_axis(bm, set(v for e in edges for v in e.verts), axis)
    roof_faces = list({f for e in edges for f in e.link_faces})
    bmesh.ops.dissolve_degenerate(bm, dist=0.01, edges=edges)

    if prop.roof_hangs:

        def has_one_roof_face(e):
            return not all([f in roof_faces for f in e.link_faces])

        roof_faces = [f for f in validate(roof_faces) if f.normal.z]
        boundary_edges = [
            e for f in roof_faces for e in f.edges if has_one_roof_face(e)
        ]
        bmesh.ops.delete(bm, geom=roof_faces, context="FACES")

        hang_edges = create_roof_hangs(bm, boundary_edges, prop.outset)
        fill_roof_faces_from_hang(bm, hang_edges, prop.thickness, axis)


def create_hip_roof(bm, faces, prop):
    """Create a hip roof
    """
    roof_hang = map_new_faces(FaceMap.ROOF_HANGS)(create_flat_roof)
    faces = roof_hang(bm, faces, prop)
    face = faces[-1]
    median = face.calc_center_median()

    dissolve_lone_verts(bm, face, list(face.edges))
    original_edges = validate(face.edges)

    # get verts in anti-clockwise order
    verts = [v for v in sort_verts_by_loops(face)]
    points = [v.co.to_tuple()[:2] for v in verts]

    # compute straight skeleton
    skeleton = skeletonize(points, [])
    bmesh.ops.delete(bm, geom=faces, context="FACES_ONLY")

    height_scale = prop.height / max([arc.height for arc in skeleton])

    # -- create edges and vertices
    skeleton_edges = create_hiproof_verts_and_edges(
        bm, skeleton, original_edges, median, height_scale
    )

    # -- create faces
    create_hiproof_faces(bm, original_edges, skeleton_edges)


def is_rectangular(faces):
    """ Determine if faces form a rectangular area
    """
    # TODO - using area to determine this can fail, better
    # have checks to determine if verts are only horizontally
    # and vertically aligned.

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
    """ sort verts in face clockwise using loops
    """
    start_loop = max(face.loops, key=lambda loop: loop.vert.co.to_tuple()[:2])

    verts = []
    current_loop = start_loop
    while len(verts) < len(face.loops):
        verts.append(current_loop.vert)
        current_loop = current_loop.link_loop_prev

    return verts


def vert_at_loc(loc, verts, loc_z=None):
    """ Find all verts at loc(x,y), return the one with highest z coord
    """
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


@map_new_faces(FaceMap.WALLS)
def extrude_up_and_delete_faces(bm, faces, extrude_depth):
    """ Extrude faces upwards and delete ones at top
    """
    ret = bmesh.ops.extrude_face_region(bm, geom=faces)
    verts = filter_geom(ret["geom"], BMVert)
    edges = filter_geom(ret["geom"], BMEdge)
    nfaces = filter_geom(ret["geom"], BMFace)
    bmesh.ops.translate(bm, verts=verts, vec=(0, 0, extrude_depth))
    bmesh.ops.delete(bm, geom=faces + nfaces, context="FACES_ONLY")
    return edges


def merge_verts_along_axis(bm, verts, axis):
    """ Merge verts that lie along given axis
    """
    key_func = operator.attrgetter("co." + axis)
    _max = max(verts, key=key_func)
    _min = min(verts, key=key_func)
    mid = getattr((_max.co + _min.co) / 2, axis)
    for v in verts:
        setattr(v.co, axis, mid)
    bmesh.ops.remove_doubles(bm, verts=bm.verts)


@map_new_faces(FaceMap.ROOF_HANGS)
def create_roof_hangs(bm, edges, size):
    """Extrude edges outwards and slope the downward to form proper
    hangs
    """
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
    """ Use edges formed for hang to form complete roof
    """
    # -- extrude edges upwards
    ret = bmesh.ops.extrude_edge_only(bm, edges=edges)
    verts = filter_geom(ret["geom"], BMVert)
    edges = filter_geom(ret["geom"], BMEdge)
    bmesh.ops.translate(bm, verts=verts, vec=(0, 0, roof_thickness))

    min_z = min([v.co.z for e in edges for v in e.verts])
    valid_edges = list(filter(lambda e: calc_edge_median(e).z != min_z, edges))
    edge_loc = set([getattr(calc_edge_median(e), axis) for e in valid_edges])

    # -- fill faces
    for loc in edge_loc:
        edges = [e for e in valid_edges if getattr(calc_edge_median(e), axis) == loc]
        ret = bmesh.ops.contextual_create(bm, geom=edges)
        add_faces_to_map(bm, ret["faces"], FaceMap.ROOF)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)


def create_hiproof_verts_and_edges(bm, skeleton, original_edges, median, height_scale):
    """ Create the vertices and edges from output of straight skeleton
    """
    skeleton_edges = []
    skeleton_verts = []
    for arc in skeleton:
        source = arc.source
        vsource = vert_at_loc(source, bm.verts)
        if not vsource:
            source_height = [arc.height for arc in skeleton if arc.source == source]
            ht = source_height.pop() * height_scale
            vsource = make_vert(bm, Vector((source.x, source.y, median.z + ht)))
            skeleton_verts.append(vsource)

        for sink in arc.sinks:
            vs = vert_at_loc(sink, bm.verts)
            if not vs:
                sink_height = min([arc.height for arc in skeleton if sink in arc.sinks])
                ht = height_scale * sink_height
                vs = make_vert(bm, Vector((sink.x, sink.y, median.z + ht)))
            skeleton_verts.append(vs)

            # create edge
            if vs != vsource:
                geom = bmesh.ops.contextual_create(bm, geom=[vsource, vs]).get("edges")
                skeleton_edges.extend(geom)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0001)

    skeleton_edges = validate(skeleton_edges)
    S_verts = {v for e in skeleton_edges for v in e.verts}
    O_verts = {v for e in original_edges for v in e.verts}
    skeleton_verts = [v for v in skeleton_verts if v in S_verts and v not in O_verts]
    return join_intersections_and_get_skeleton_edges(bm, skeleton_verts, skeleton_edges)


@map_new_faces(FaceMap.ROOF)
def create_hiproof_faces(bm, original_edges, skeleton_edges):
    """ Create faces formed from hiproof verts and edges
    """
    for ed in validate(original_edges):
        verts = ed.verts
        linked_skeleton_edges = get_linked_edges(verts, skeleton_edges)
        all_verts = [v for e in linked_skeleton_edges for v in e.verts]
        opposite_verts = list(set(all_verts) - set(verts))

        if len(opposite_verts) == 1:
            # -- triangle
            bmesh.ops.contextual_create(bm, geom=linked_skeleton_edges + [ed])
        else:
            edge = bm.edges.get(opposite_verts)
            if edge:
                # -- quad
                geometry = linked_skeleton_edges + [ed, edge]
                bmesh.ops.contextual_create(bm, geom=geometry)
            else:
                # -- polygon
                edges = cycle_edges_form_polygon(
                    bm, opposite_verts, skeleton_edges, linked_skeleton_edges
                )
                bmesh.ops.contextual_create(bm, geom=[ed] + edges)


def make_vert(bm, location):
    """ Create a vertex at location
    """
    return bmesh.ops.create_vert(bm, co=location).get("vert").pop()


def join_intersecting_verts_and_edges(bm, edges, verts):
    """ Find all vertices that intersect/ lie at an edge and merge
    them to that edge
    """
    new_verts = []
    for v in verts:
        for e in edges:
            if v in e.verts:
                continue

            v1, v2 = e.verts
            res = mathutils.geometry.intersect_line_line_2d(v.co, v.co, v1.co, v2.co)
            if res is not None:
                split_vert = v1
                split_factor = (v1.co - v.co).length / e.calc_length()
                new_edge, new_vert = bmesh.utils.edge_split(e, split_vert, split_factor)
                new_verts.append(new_vert)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.01)
    return validate(new_verts)


def get_linked_edges(verts, filter_edges):
    """ Find all the edges linked to verts that are also in filter edges
    """
    linked_edges = [e for v in verts for e in v.link_edges]
    return list(filter(lambda e: e in filter_edges, linked_edges))


def find_closest_pair_edges(edges_a, edges_b):
    """ Find the edges in edges_a and edges_b that are closest to each other
    """

    def length_func(pair):
        e1, e2 = pair
        return (calc_edge_median(e1) - calc_edge_median(e2)).length

    pairs = [(e1, e2) for e1 in edges_a for e2 in edges_b]
    return sorted(pairs, key=length_func)[0]


def join_intersections_and_get_skeleton_edges(bm, skeleton_verts, skeleton_edges):
    """ Join intersecting edges and verts and return all edges that are in skeleton_edges
    """
    new_verts = join_intersecting_verts_and_edges(bm, skeleton_edges, skeleton_verts)
    skeleton_verts = validate(skeleton_verts) + new_verts
    return list(set(e for v in skeleton_verts for e in v.link_edges))


def dissolve_lone_verts(bm, face, original_edges):
    """ Find all verts only connected to two edges and dissolve them
    """
    loops = {loop for v in face.verts for loop in v.link_loops if loop.face == face}

    def is_parallel(loop):
        return round(loop.calc_angle(), 3) == 3.142

    parallel_verts = [loop.vert for loop in loops if is_parallel(loop)]
    lone_edges = [
        e for v in parallel_verts for e in v.link_edges if e not in original_edges
    ]
    bmesh.ops.dissolve_edges(bm, edges=lone_edges, use_verts=True)


def cycle_edges_form_polygon(bm, verts, skeleton_edges, linked_edges):
    """ Move in opposite directions along edges linked to verts until
    you form a polygon
    """
    v1, v2 = verts
    next_skeleton_edges = list(set(skeleton_edges) - set(linked_edges))
    v1_edges = get_linked_edges([v1], next_skeleton_edges)
    v2_edges = get_linked_edges([v2], next_skeleton_edges)
    if not v1_edges or not v2_edges:
        return linked_edges
    pair = find_closest_pair_edges(v1_edges, v2_edges)

    all_verts = [v for e in pair for v in e.verts]
    verts = list(set(all_verts) - set(verts))
    if len(verts) == 1:
        return linked_edges + list(pair)
    else:
        edge = bm.edges.get(verts)
        if edge:
            return list(pair) + linked_edges + [edge]
        else:
            return cycle_edges_form_polygon(
                bm, verts, skeleton_edges, linked_edges + list(pair)
            )
