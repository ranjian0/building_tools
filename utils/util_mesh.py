import bpy
import bmesh
from mathutils import Matrix, Vector
from bmesh.types import BMVert


def get_edit_mesh():
    """ Get editmode mesh """
    return bpy.context.edit_object.data


def make_mesh(name):
    """ Make new mesh data """
    return bpy.data.meshes.new(name)


def select(elements, val=True):
    """ For each item in elements set select to val """
    for el in elements:
        el.select = val


def filter_geom(geom, _type):
    """ Find all elements ot type _type in geom iterable """
    return list(filter(lambda x: isinstance(x, _type), geom))


def filter_vertical_edges(edges, normal):
    """ Determine edges that are vertical based on a normal value """
    res = []
    rnd = lambda val: round(val, 4)

    for e in edges:
        if normal.z:
            s = set([rnd(v.co.x) for v in e.verts])
        elif normal.y:
            s = set([rnd(v.co.x) for v in e.verts])
        else:
            s = set([rnd(v.co.y) for v in e.verts])
        if len(s) == 1:
            res.append(e)
    return res


def filter_horizontal_edges(edges, normal):
    """ Determine edges that are horizontal based on a normal value """
    res = []
    rnd = lambda val: round(val, 4)

    for e in edges:
        if normal.z:
            s = set([rnd(v.co.y) for v in e.verts])
        elif normal.y:
            s = set([rnd(v.co.z) for v in e.verts])
        else:
            s = set([rnd(v.co.z) for v in e.verts])
        if len(s) == 1:
            res.append(e)
    return res


def calc_edge_median(edge):
    """ Calculate the center position of edge """
    mx = sum([v.co.x for v in edge.verts])
    my = sum([v.co.y for v in edge.verts])
    mz = sum([v.co.z for v in edge.verts])
    return Vector((mx / 2, my / 2, mz / 2))


def calc_verts_median(verts):
    """ Determine the median position of verts """
    mx = sum([v.co.x for v in verts])
    my = sum([v.co.y for v in verts])
    mz = sum([v.co.z for v in verts])
    return Vector((mx / 2, my / 2, mz / 2))


def calc_face_dimensions(face):
    """ Determine the width and height of face """
    if face.normal.x and not face.normal.y:
        width = max([v.co.y for v in face.verts]) - \
            min([v.co.y for v in face.verts])
    elif face.normal.y and not face.normal.x:
        width = max([v.co.x for v in face.verts]) - \
            min([v.co.x for v in face.verts])
    elif face.normal.x and face.normal.y:
        v1 = max([v.co for v in face.verts], key=lambda v: v.x)
        v2 = min([v.co for v in face.verts], key=lambda v: v.x)
        width = (v1 - v2).length
    else:
        width = 0

    height = max([v.co.z for v in face.verts]) - \
        min([v.co.z for v in face.verts])
    return width, height


def calc_edge_orient(edge):
    """ Determine the orientation of edge """
    x_coords = list(set([round(v.co.x, 1) for v in edge.verts]))
    y_coords = list(set([round(v.co.y, 1) for v in edge.verts]))
    z_coords = list(set([round(v.co.z, 1) for v in edge.verts]))

    if len(x_coords) == 1 or len(y_coords) == 1:
        return Vector((0, 0, 1))
    elif len(z_coords) == 1 and len(y_coords) == 1:
        return Vector((1, 0, 0))
    elif len(z_coords) == 1 and len(x_coords) == 1:
        return Vector((0, 1, 0))
    else:
        return Vector((0, 0, 0))


def square_face(bm, face):
    """ Make face square if it is rectangular """
    max_length = max([e.calc_length() for e in face.edges])
    min_length = min([e.calc_length() for e in face.edges])

    scale_factor = max_length / min_length
    min_edge = list(filter(lambda e: e.calc_length() == min_length,
                           face.edges))[-1]

    if calc_edge_orient(min_edge).x:
        scale_vec = (scale_factor, 1, 1)
    elif calc_edge_orient(min_edge).y:
        scale_vec = (1, scale_factor, 1)
    elif calc_edge_orient(min_edge).z:
        scale_vec = (1, 1, scale_factor)
    else:
        scale_vec = (1, 1, 1)

    fc = face.calc_center_median()
    bmesh.ops.scale(bm, verts=list(face.verts), vec=scale_vec,
                    space=Matrix.Translation(-fc))


def face_with_verts(bm, verts):
    """ Find a face in the bmesh with the given verts"""
    for face in bm.faces:
        if len(set(list(face.verts) + verts)) == len(verts):
            return face
    return None


def split_quad(vertical=False, cuts=4):
    """ Subdivide a quad's edges into even horizontal/vertical cuts """
    me = get_edit_mesh()
    bm = bmesh.from_edit_mesh(me)

    # Find selected faces
    faces = [f for f in bm.faces if face.select]

    for face in faces:
        if vertical:
            e = filter_horizontal_edges(face.edges, face.normal)
            res = bmesh.ops.subdivide_edges(bm, edges=e, cuts=cuts)
        else:
            e = filter_vertical_edges(face.edges, face.normal)
            res = bmesh.ops.subdivide_edges(bm, edges=e, cuts=cuts)

    bmesh.update_edit_mesh(me, True)
    return res


def split(bm, face, svertical=2, shorizontal=2, offx=0, offy=0, offz=0):
    """ Split a quad into regular quad sections (basically an inset with only right-angled edges) """

    face.select = False
    # MAKE VERTICAL SPLIT
    # ---------------------

    # Determine horizontal edges
    # --  edges whose verts have similar z coord
    horizontal = list(filter(lambda e: len(
        set([round(v.co.z, 1) for v in e.verts])) == 1, face.edges))

    median = face.calc_center_median()
    # Subdivide edges
    sp_res = bmesh.ops.subdivide_edges(bm, edges=horizontal, cuts=2)
    hverts = filter_geom(sp_res['geom_inner'], BMVert)

    # Scale subdivide face
    T = Matrix.Translation(-median)
    sv = face.normal.cross(Vector((0, 0, 1)))
    scale_vector = (abs(sv.x) * shorizontal if sv.x else 1, abs(sv.y) * shorizontal if sv.y else 1,
                    abs(sv.z) * shorizontal if sv.z else 1)
    bmesh.ops.scale(bm, vec=scale_vector, verts=hverts, space=T)

    # MAKE HORIZONTAL SPLIT
    # ---------------------

    bmesh.ops.remove_doubles(bm, verts=list(bm.verts))
    face = face_with_verts(bm, hverts)

    # Determine vertical edges
    # -- edges whose verts have similar x/y coord
    other = list(filter(lambda e: len(
        set([round(v.co.z, 1) for v in e.verts])) == 1, face.edges))
    vertical = list(set(face.edges).difference(other))

    # Subdivide
    sp_res = bmesh.ops.subdivide_edges(bm, edges=vertical, cuts=2)
    verts = filter_geom(sp_res['geom_inner'], BMVert)

    # Scale subdivide face
    T = Matrix.Translation(-median)
    bmesh.ops.scale(bm, vec=(1, 1, svertical), verts=verts, space=T)

    # OFFSET VERTS
    # ---------------------
    link_edges = [e for v in verts for e in v.link_edges]
    all_verts = list(set([v for e in link_edges for v in e.verts]))
    bmesh.ops.translate(bm, verts=all_verts, vec=(offx, offy, 0))
    bmesh.ops.translate(bm, verts=verts, vec=(0, 0, offz))

    # CLEANUP
    # --------

    # -- delete faces with area less than min_area
    min_area = 0.01
    del_faces = []
    for f in bm.faces:
        if face.calc_area() < min_area:
            del_faces.append(f)

    if del_faces:
        bmesh.ops.delete(bm, geom=del_faces, context=3)
    select(bm.faces, False)

    face = face_with_verts(bm, verts)

    # -- remove doubles
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts))

    return face


def facedata_from_index(obj, index):
    """ Determine unique properties of the face with the given index """

    properties = dict()
    face = obj.data.polygons[index]

    # -- normal
    properties['normal'] = face.normal 

    # -- floor
    fcount = obj.building.floors.floor_count
    fheight = obj.building.floors.floor_height
    sthick = obj.building.floors.slab_thickness
    pos = round(face.center[2], 2)

    for i in range(fcount):
        current_slab = sthick/2 + (i * fheight) + (i * (sthick/2))
        current_floor = fheight/2 + ((i+1) * sthick) + (i * fheight)

        if pos == round(current_slab, 2):
            properties['type'] = 'SLAB'
            properties['floor'] = i 
            break
        elif pos == round(current_floor, 2):
            properties['type'] = 'FLOOR'
            properties['floor'] = i 
            break

    # -- floor index
    # if the floor has multiple faces in a given normal direction,
    # floor index is the clockwise id of the face
    polys = [p for p in obj.data.polygons if 
        p.normal == face.normal and p.center[2] == face.center[2]    
    ]
    if polys:
        polys = sorted(polys, key=lambda p : p.center[0])
        polys = sorted(polys, key=lambda p : p.center[1])
        polys = sorted(polys, key=lambda p : p.center[2])

        index = [idx for idx, p in enumerate(polys) if p == face][-1]
    else:
        index = 0
    properties['floor_index'] = index

    return properties

def index_from_facedata(obj, bm, face_data):
    """ Determine the index of a face give some face data """
    all_faces = bm.faces

    # -- filter the faces with normal
    normal = face_data.get("normal")
    all_faces = filter(lambda f : f.normal.to_tuple(1) == tuple(normal),
                        all_faces)

    # -- filter faces with the floor number and type
    fheight = obj.building.floors.floor_height
    sthick = obj.building.floors.slab_thickness

    floor = face_data.get('floor')
    if face_data.get('type') == 'SLAB':
        target_height = sthick/2 + (floor * fheight) + (floor * (sthick/2))
    elif face_data.get('type') == 'FLOOR':
        target_height = fheight/2 + ((floor+1) * sthick) + (floor * fheight)


    _all_faces = []
    for face in all_faces:
        center = round(face.calc_center_median().z, 2)
        target = round(target_height, 2)
        if center == target:
            _all_faces.append(face)

    # -- filter faces with floor index
    all_faces = sorted(_all_faces, key=lambda f : f.calc_center_median().x)
    all_faces = sorted(all_faces, key=lambda f : f.calc_center_median().y)
    all_faces = sorted(all_faces, key=lambda f : f.calc_center_median().z)

    index = face_data.get('floor_index')
    ret = all_faces[index]

    return ret.index
