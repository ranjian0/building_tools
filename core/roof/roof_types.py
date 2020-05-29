import bmesh
import mathutils
from mathutils import Vector, Matrix
from bmesh.types import BMVert, BMEdge, BMFace
from ...utils import (
    equal,
    select,
    FaceMap,
    validate,
    edge_vector,
    skeletonize,
    filter_geom,
    popup_message,
    map_new_faces,
    calc_edge_median,
    add_faces_to_map,
    calc_verts_median,
    set_roof_type_hip,
    set_roof_type_gable,
    filter_vertical_edges,
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


def create_gable_roof_old(bm, faces, prop):
    """Create a gable roof
    """
    if len(faces) > 1:
        faces = bmesh.ops.dissolve_faces(bm, faces=faces, use_verts=True).get("region")

    if not is_rectangular(faces[0]):
        popup_message("Gable Roof can only be created on rectangular faces", "Context Error")
        return

    edges = extrude_up_and_delete_faces(bm, faces, prop.height)
    sedges = sorted(edges, key=lambda e: e.calc_length())
    normal_edge = edge_vector(sedges[0])
    if prop.flip_direction:
        normal_edge = edge_vector(sedges[-1])

    # -- cleanup any lone edges
    if len(edges) > 4:
        sverts = list({v for e in sedges for v in e.verts})
        lone_edges = [e for v in sverts for e in v.link_edges if e not in sedges and equal(e.calc_face_angle(), 0)]
        bmesh.ops.dissolve_edges(bm, edges=lone_edges, use_verts=True)
        edges = validate(edges)

    merge_normal = normal_edge.cross(Vector((0, 0, 1)))
    merge_edges_along_normal(bm, edges, merge_normal)
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
        fill_roof_faces_from_hang(bm, hang_edges, prop.thickness)


def create_gable_roof(bm, faces, prop):
    if prop.gable_type == "BOX":
        roof_hang = map_new_faces(FaceMap.ROOF_HANGS)(create_flat_roof)
        faces = roof_hang(bm, faces, prop)

    if len(faces) > 1:
        faces = bmesh.ops.dissolve_faces(bm, faces=faces, use_verts=True).get("region")

    face = faces[-1]
    median = face.calc_center_median()

    dissolve_lone_verts(bm, face, list(face.edges))
    original_edges = validate(face.edges)

    # get verts in anti-clockwise order
    verts = [v for v in sort_verts_by_loops(face)]
    points = [v.co.to_tuple()[:2] for v in verts]

    # compute straight skeleton
    set_roof_type_gable()
    skeleton = skeletonize(points, [])
    bmesh.ops.delete(bm, geom=faces, context="FACES_ONLY")

    height_scale = prop.height / max([arc.height for arc in skeleton])

    # -- create edges and vertices
    skeleton_edges = create_hiproof_verts_and_edges(
        bm, skeleton, original_edges, median, height_scale
    )

    # -- create faces
    roof_faces = create_hiproof_faces(bm, original_edges, skeleton_edges)
    if prop.gable_type == "OPEN":
        gable_process_open(bm, roof_faces, prop)
    elif prop.gable_type == "BOX":
        gable_process_box(bm, roof_faces, prop)


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
    set_roof_type_hip()
    skeleton = skeletonize(points, [])
    bmesh.ops.delete(bm, geom=faces, context="FACES_ONLY")

    height_scale = prop.height / max([arc.height for arc in skeleton])

    # -- create edges and vertices
    skeleton_edges = create_hiproof_verts_and_edges(
        bm, skeleton, original_edges, median, height_scale
    )

    # -- create faces
    create_hiproof_faces(bm, original_edges, skeleton_edges)


def is_rectangular(face):
    """ Determine if faces form a rectangular polygon
    Current strategies may fail, when that happens, consider strategies from
    https://www.quora.com/How-do-you-know-if-a-polygon-is-regular
    """
    verts = list(face.verts)
    loops = list({loop for v in face.verts for loop in v.link_loops if loop.face == face})

    # -- strategy A (only 4 right angled verts, others colinear)
    # no problem if the face is an ngon
    angles = [l.calc_angle() for l in loops]
    right_angles = [a for a in angles if round(a, 2) == 1.57]
    other_angles = [a for a in angles if a not in right_angles and round(a, 2) == 3.14]
    strat_b = len(right_angles) == 4 and (len(right_angles) + len(other_angles)) == len(angles)
    if not strat_b:
        return False

    # -- strategy B (equal diagonals)
    verts = sorted(verts, key=lambda v: (v.co.x, v.co.y))
    _min_x, _max_x = verts[0], verts[-1]

    verts = sorted(verts, key=lambda v: (v.co.y, v.co.x))
    _min_y, _max_y = verts[0], verts[-1]

    diag_a = round((_min_x.co - _max_x.co).length, 4)
    diag_b = round((_min_y.co - _max_y.co).length, 4)
    if not diag_a == diag_b:
        return False

    # -- strategy C (face area ~= numerical area)
    a, b = abs(_max_x.co.x - _min_x.co.x), abs(_max_y.co.y - _min_y.co.y)
    num_area = a * b
    if not equal(face.calc_area(), num_area):
        return False
    return True


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


def merge_edges_along_normal(bm, edges, normal):
    """ Merge verts so that they lie along the midpoint perpendicular to a normal
    """
    def vabs(vec):
        return tuple(map(abs, vec.to_tuple(3)))

    for edge in edges:
        if vabs(edge_vector(edge)) == vabs(normal):
            cen = calc_edge_median(edge)
            for v in edge.verts:
                v.co = cen
    bmesh.ops.remove_doubles(bm, verts=bm.verts)


@map_new_faces(FaceMap.ROOF_HANGS)
def create_roof_hangs(bm, edges, size):
    """Extrude edges outwards and slope the downward to form proper hangs
    """
    ret = bmesh.ops.extrude_edge_only(bm, edges=edges)
    verts = filter_geom(ret["geom"], BMVert)
    bmesh.ops.scale(bm, verts=verts, vec=(1 + size, 1 + size, 1),
                    space=Matrix.Translation(-calc_verts_median(verts)))

    hang_edges = list(
        {e for v in verts for e in v.link_edges if all([v in verts for v in e.verts])}
    )

    # -- fix roof slope at bottom edges
    min_loc_z = min([v.co.z for e in hang_edges for v in e.verts])
    min_verts = list({v for e in hang_edges for v in e.verts if v.co.z == min_loc_z})
    bmesh.ops.translate(bm, verts=min_verts, vec=(0, 0, -size))
    return hang_edges


def fill_roof_faces_from_hang(bm, edges, roof_thickness):
    """ Use edges formed for hang to form complete roof
    """
    # -- extrude edges upwards
    ret = bmesh.ops.extrude_edge_only(bm, edges=edges)
    verts = filter_geom(ret["geom"], BMVert)
    edges = filter_geom(ret["geom"], BMEdge)
    bmesh.ops.translate(bm, verts=verts, vec=(0, 0, roof_thickness))

    min_z = min([v.co.z for e in edges for v in e.verts])
    valid_edges = list(filter(lambda e: calc_edge_median(e).z != min_z, edges))
    ret = bmesh.ops.bridge_loops(bm, edges=valid_edges, use_pairs=True)
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
    result = []
    for ed in validate(original_edges):
        verts = ed.verts
        linked_skeleton_edges = get_linked_edges(verts, skeleton_edges)
        all_verts = [v for e in linked_skeleton_edges for v in e.verts]
        opposite_verts = list(set(all_verts) - set(verts))

        if len(opposite_verts) == 1:
            # -- triangle
            r = bmesh.ops.contextual_create(bm, geom=linked_skeleton_edges + [ed])
            result.extend(r.get('faces', []))
        else:
            edge = bm.edges.get(opposite_verts)
            if edge:
                # -- quad
                geometry = linked_skeleton_edges + [ed, edge]
                r = bmesh.ops.contextual_create(bm, geom=geometry)
                result.extend(r.get('faces', []))
            else:
                # -- polygon
                edges = cycle_edges_form_polygon(
                    bm, opposite_verts, skeleton_edges, linked_skeleton_edges
                )
                r = bmesh.ops.contextual_create(bm, geom=[ed] + edges)
                result.extend(r.get('faces', []))
    return result


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
        return round(loop.calc_angle(), 2) == 3.14

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


def gable_process_box(bm, roof_faces, prop):
    """ Create box gable roof type
    """
    # -- extrude new faces and move up
    top_faces = [f for f in roof_faces if f.normal.z]
    result = bmesh.ops.extrude_face_region(bm, geom=top_faces).get("geom")
    new_verts = filter_geom(result, BMVert)
    bmesh.ops.translate(bm, verts=new_verts, vec=(0, 0, prop.thickness))
    bmesh.ops.delete(bm, geom=top_faces, context="FACES")


def gable_process_open(bm, roof_faces, prop):
    """ Create open gable roof type
    """
    # -- find only the upward facing faces
    top_faces = [f for f in roof_faces if f.normal.z]

    # -- extrude and move up
    result = bmesh.ops.extrude_face_region(bm, geom=top_faces).get("geom")
    new_verts = filter_geom(result, BMVert)
    bmesh.ops.translate(bm, verts=new_verts, vec=(0, 0, prop.thickness))
    bmesh.ops.delete(bm, geom=top_faces, context="FACES")

    # -- find new created side faces
    side_faces = []
    new_faces = filter_geom(result, BMFace)
    for f in new_faces:
        for e in f.edges:
            link_faces = e.link_faces
            len_valid = len(link_faces) == 2
            link_valid = sum([f in new_faces for f in link_faces]) == 1

            if len_valid and link_valid:
                side_faces.extend(set(link_faces) - set(new_faces))

    # -- outset faces along
    bmesh.ops.inset_region(
        bm, use_even_offset=True, faces=side_faces, depth=prop.outset).get("faces")

    # -- move lower vertical edges abit down (inorder to maintain roof slope)
    v_edges = []
    for f in side_faces:
        v_edges.extend(filter_vertical_edges(f.edges, f.normal))

    # -- find ones with lowest z
    min_z = min([calc_edge_median(e).z for e in v_edges])
    min_z_edges = [e for e in v_edges if calc_edge_median(e).z == min_z]
    min_z_verts = list(set(v for e in min_z_edges for v in e.verts))
    bmesh.ops.translate(bm, verts=min_z_verts, vec=(0, 0, -prop.thickness/2))
