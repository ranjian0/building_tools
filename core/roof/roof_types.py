import bpy
import bmesh

from bmesh.types import BMVert, BMEdge, BMFace
from ...utils import (
    select,
    filter_geom,
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

    bmesh.ops.inset_region(bm, faces=link_faces, depth=outset)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)

    bmesh.ops.delete(bm,
        geom=faces,
        context=5)


def make_gable_roof(bm, faces, **kwargs):
    if not rectangular_area(faces):
        return

    if len(faces) == 1:
        pass
    else:
        pass


def make_hip_roof(bm, faces, **kwargs):
    pass

def rectangular_area(faces):
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