import bmesh
import mathutils
import numpy as np
from bmesh.types import BMVert, BMFace
from mathutils import Vector

from ...utils import (
    equal,
    select,
    FaceMap,
    validate,
    edge_vector,
    skeletonize,
    filter_geom,
    map_new_faces,
    popup_message,
    edge_is_vertical,
    add_faces_to_map,
    calc_edge_median,
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
    # -- extrude up and outset
    top_face = extrude_and_outset(bm, faces, prop.thickness, prop.outset)

    # -- add border
    if prop.add_border:
        # -- inset top face
        bmesh.ops.inset_region(
            bm, faces=top_face, thickness=prop.border, use_even_offset=True
        )

        # -- extrude downwards
        ret = bmesh.ops.extrude_face_region(bm, geom=top_face).get("geom")
        bmesh.ops.translate(
            bm, vec=(0, 0, -(prop.thickness - 0.0011)), verts=filter_geom(ret, BMVert)
        )
        bmesh.ops.delete(bm, geom=top_face, context="FACES")


def create_gable_roof(bm, faces, prop):
    """ Create gable roof
    """
    # -- create initial outset for box gable roof
    if prop.gable_type == "BOX":
        faces = extrude_and_outset(bm, faces, prop.thickness, prop.outset)
        link_faces = {f for fa in faces for e in fa.edges for f in e.link_faces}
        all_edges = {e for f in link_faces for e in f.edges}
        bmesh.ops.delete(bm, geom=list(link_faces), context="FACES")
        faces = bmesh.ops.contextual_create(bm, geom=validate(all_edges)).get("faces")

        bot_faces = [f for e in faces[-1].edges for f in e.link_faces if f not in faces]
        add_faces_to_map(bm, bot_faces, FaceMap.ROOF_HANGS)
    else:
        # -- Open GABLE
        #  XXX prevent dissolve_lone_verts from destroying lower geometry
        ret = bmesh.ops.extrude_face_region(bm, geom=faces).get("geom")
        bmesh.ops.translate(
            bm, vec=(0, 0, 0.0011), verts=filter_geom(ret, BMVert)
        )
        bmesh.ops.delete(bm, geom=faces, context="FACES")
        faces = filter_geom(ret, BMFace)

    # -- dissolve if faces are many
    if len(faces) > 1:
        faces = bmesh.ops.dissolve_faces(bm, faces=faces, use_verts=True).get("region")
    face = faces[-1]
    median = face.calc_center_median()

    # -- remove verts that are between two parallel edges
    dissolve_lone_verts(bm, face, list(face.edges))
    original_edges = validate(face.edges)

    # -- get verts in anti-clockwise order (required by straight skeleton)
    verts = [v for v in sort_verts_by_loops(face)]
    points = [v.co.to_tuple()[:2] for v in verts]

    # -- compute straight skeleton
    skeleton = skeletonize(points, [], zero_gradient=True)
    bmesh.ops.delete(bm, geom=faces, context="FACES_ONLY")

    height_scale = prop.height / max([arc.height for arc in skeleton])

    # -- create edges and vertices
    skeleton_edges = create_skeleton_verts_and_edges(
        bm, skeleton, original_edges, median, height_scale
    )

    # -- create faces
    roof_faces = create_skeleton_faces(bm, original_edges, skeleton_edges)
    if prop.gable_type == "OPEN":
        gable_process_open(bm, roof_faces, prop)
    elif prop.gable_type == "BOX":
        gable_process_box(bm, roof_faces, prop)


def create_hip_roof(bm, faces, prop):
    """Create a hip roof
    """
    # -- create base for hip roof
    roof_hang = map_new_faces(FaceMap.ROOF_HANGS)(extrude_and_outset)
    faces = roof_hang(bm, faces, prop.thickness, prop.outset)
    face = faces[-1]
    median = face.calc_center_median()

    # -- remove verts that are between two parallel edges
    dissolve_lone_verts(bm, face, list(face.edges))
    original_edges = validate(face.edges)

    # -- get verts in anti-clockwise order
    verts = [v for v in sort_verts_by_loops(face)]
    points = [v.co.to_tuple()[:2] for v in verts]

    # -- compute straight skeleton
    skeleton = skeletonize(points, [])
    bmesh.ops.delete(bm, geom=faces, context="FACES_ONLY")

    height_scale = prop.height / max([arc.height for arc in skeleton])

    # -- create edges and vertices
    skeleton_edges = create_skeleton_verts_and_edges(
        bm, skeleton, original_edges, median, height_scale
    )

    # -- create faces
    create_skeleton_faces(bm, original_edges, skeleton_edges)


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


def create_skeleton_verts_and_edges(bm, skeleton, original_edges, median, height_scale):
    """ Create the vertices and edges from output of straight skeleton
    """
    skeleton_edges = []
    skeleton_verts = []
    O_verts = list({v for e in original_edges for v in e.verts})
    for arc in skeleton:
        source = arc.source
        vsource = vert_at_loc(source, O_verts + skeleton_verts)
        if not vsource:
            source_height = [arc.height for arc in skeleton if arc.source == source]
            ht = source_height.pop() * height_scale
            vsource = make_vert(bm, Vector((source.x, source.y, median.z + ht)))
            skeleton_verts.append(vsource)

        for sink in arc.sinks:
            vs = vert_at_loc(sink, O_verts + skeleton_verts)
            if not vs:
                sink_height = min([arc.height for arc in skeleton if sink in arc.sinks])
                ht = height_scale * sink_height
                vs = make_vert(bm, Vector((sink.x, sink.y, median.z + ht)))
            skeleton_verts.append(vs)

            # create edge
            if vs != vsource:
                geom = bmesh.ops.contextual_create(bm, geom=[vsource, vs]).get("edges")
                skeleton_edges.extend(geom)

    skeleton_edges = validate(skeleton_edges)
    S_verts = list({v for e in skeleton_edges for v in e.verts} - set(O_verts))
    return join_intersections_and_get_skeleton_edges(bm, S_verts, skeleton_edges)


@map_new_faces(FaceMap.ROOF)
def create_skeleton_faces(bm, original_edges, skeleton_edges):
    """ Create faces formed from hiproof verts and edges
    """

    def interior_angle(vert, e1, e2):
        """ Determine anti-clockwise interior angle between edges
        https://stackoverflow.com/questions/2827393/angles-between-two-n-dimensional-vectors-in-python
        """
        # XXX Order of vector creation is really important
        v1 = vert.co - e1.other_vert(vert).co
        v2 = e2.other_vert(vert).co - vert.co
        return np.math.atan2(np.linalg.det([v1.xy, v2.xy]), np.dot(v1.xy, v2.xy))

    def boundary_walk(e, reverse=False):
        """ Perform boundary walk using least interior angle
        """
        v, last = e.verts
        if reverse:
            last, v = e.verts

        previous = e
        found_edges = [e]
        while v != last:
            linked = [
                e for e in v.link_edges if e in skeleton_edges and e not in found_edges
            ]
            if not linked:
                common_edge = set(v.link_edges) & set(last.link_edges)
                if common_edge:
                    found_edges.append(common_edge.pop())
                    break
                # Re-walk if we have not reversed already, otherwise fail quietly
                return boundary_walk(e, True) if not reverse else []

            next_edge = linked[0]
            if len(linked) > 1:
                next_edge = min(linked, key=lambda e: interior_angle(v, previous, e))
            previous = next_edge
            found_edges.append(next_edge)
            v = next_edge.other_vert(v)

        return found_edges

    result = []
    for ed in validate(original_edges):
        walk = boundary_walk(ed)
        if len(walk) < 3:
            # XXX Geometry error caused by intersecting roof edges
            # esp when outset property is set high on concave polygons

            # -- try to help user
            popup_message("Roof Intersection Detected. Adjust(decrease) roof 'outset'", title="Geometry Error")
            continue
        result.extend(bmesh.ops.contextual_create(bm, geom=walk).get("faces"))
    return result


def make_vert(bm, location):
    """ Create a vertex at location
    """
    return bmesh.ops.create_vert(bm, co=location).get("vert").pop()


def join_intersecting_verts_and_edges(bm, edges, verts):
    """ Find all vertices that intersect/ lie at an edge and merge
        them to that edge
    """
    eps = 0.0001
    new_verts = []
    for v in verts:
        for e in edges:
            if v in e.verts:
                continue

            v1, v2 = e.verts
            ortho = edge_vector(e).orthogonal().normalized() * eps
            res = mathutils.geometry.intersect_line_line_2d(v.co, v.co, v1.co, v2.co)
            if res is None:
                res = mathutils.geometry.intersect_line_line_2d(v.co - ortho, v.co + ortho, v1.co, v2.co)

            if res:
                split_vert = v1
                split_factor = (v1.co - v.co).length / e.calc_length()
                new_edge, new_vert = bmesh.utils.edge_split(e, split_vert, split_factor)
                new_verts.append(new_vert)
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
    bmesh.ops.remove_doubles(bm, verts=skeleton_verts, dist=0.0001)
    return list(set(e for v in validate(skeleton_verts) for e in v.link_edges))


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


def gable_process_box(bm, roof_faces, prop):
    """ Finalize box gable roof type
    """
    # -- extrude upward faces
    top_faces = [f for f in roof_faces if f.normal.z]
    result = bmesh.ops.extrude_face_region(bm, geom=top_faces).get("geom")

    # -- move abit upwards (by amount roof thickness)
    bmesh.ops.translate(
        bm, verts=filter_geom(result, BMVert), vec=(0, 0, prop.thickness)
    )
    bmesh.ops.delete(bm, geom=top_faces, context="FACES")

    # -- face maps
    link_faces = {
        f for fc in filter_geom(result, BMFace) for e in fc.edges
        for f in e.link_faces if not f.normal.z
    }
    link_faces.update(set(validate(roof_faces)))
    add_faces_to_map(bm, list(link_faces), FaceMap.ROOF_HANGS)


def gable_process_open(bm, roof_faces, prop):
    """ Finalize open gable roof type
    """
    add_faces_to_map(bm, roof_faces, FaceMap.WALLS)

    # -- find only the upward facing faces
    top_faces = [f for f in roof_faces if f.normal.z]

    # -- extrude and move up
    result = bmesh.ops.extrude_face_region(bm, geom=top_faces).get("geom")
    bmesh.ops.translate(
        bm, verts=filter_geom(result, BMVert), vec=(0, 0, prop.thickness)
    )
    bmesh.ops.delete(bm, geom=top_faces, context="FACES")

    # -- find newly created side faces
    side_faces = []
    new_faces = filter_geom(result, BMFace)
    for e in [ed for f in new_faces for ed in f.edges]:
        link_faces = e.link_faces
        len_valid = len(link_faces) == 2
        link_valid = sum([f in new_faces for f in link_faces]) == 1

        if len_valid and link_valid:
            side_faces.extend(set(link_faces) - set(new_faces))

    # --determine upper bounding edges to be dissolved after outset
    dissolve_edges = []
    for f in side_faces:
        v_edges = list(filter(edge_is_vertical, f.edges))
        edges = list(set(f.edges) - set(v_edges))
        max_edge = max(edges, key=lambda e: calc_edge_median(e).z)
        dissolve_edges.append(max_edge)

    # -- outset side faces
    bmesh.ops.inset_region(
        bm, use_even_offset=True, faces=side_faces, depth=prop.outset
    )

    # -- move lower vertical edges abit down (inorder to maintain roof slope)
    v_edges = []
    for f in side_faces:
        v_edges.extend(list(filter(edge_is_vertical, f.edges)))

    # -- find ones with lowest z
    min_z = min([calc_edge_median(e).z for e in v_edges])
    min_z_edges = [e for e in v_edges if calc_edge_median(e).z == min_z]
    min_z_verts = list(set(v for e in min_z_edges for v in e.verts))
    bmesh.ops.translate(bm, verts=min_z_verts, vec=(0, 0, -prop.outset / 2))

    # -- post cleanup
    bmesh.ops.dissolve_edges(bm, edges=dissolve_edges)

    # -- facemaps
    linked = {f for fc in side_faces for e in fc.edges for f in e.link_faces}
    linked_top = [f for f in linked if f.normal.z > 0]
    linked_bot = [f for f in linked if f.normal.z < 0]
    add_faces_to_map(bm, linked_top, FaceMap.ROOF)
    add_faces_to_map(bm, side_faces + linked_bot, FaceMap.ROOF_HANGS)


def extrude_and_outset(bm, faces, thickness, outset):
    """ Extrude the given faces upwards and outset resulting side faces
    """
    # -- extrude faces upwards
    ret = bmesh.ops.extrude_face_region(bm, geom=faces)
    bmesh.ops.translate(
        bm, vec=(0, 0, thickness), verts=filter_geom(ret["geom"], BMVert)
    )

    # -- dissolve top faces if they are more than one
    top_face = filter_geom(ret["geom"], BMFace)
    if len(top_face) > 1:
        top_face = bmesh.ops.dissolve_faces(
            bm, faces=top_face, use_verts=True).get("region").pop()
    else:
        top_face = top_face.pop()

    # -- outset the side faces from earlier extrusion
    link_faces = [f for e in top_face.edges for f in e.link_faces if f is not top_face]

    bmesh.ops.inset_region(
        bm, faces=link_faces, depth=outset, use_even_offset=True
    )

    # -- cleanup hidden faces
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bmesh.ops.delete(bm, geom=faces, context="FACES")

    new_faces = list({f for e in top_face.edges for f in e.link_faces})
    return bmesh.ops.dissolve_faces(bm, faces=new_faces).get("region")
