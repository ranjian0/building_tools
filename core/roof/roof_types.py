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
    pass

def make_hip_roof(bm, faces, **kwargs):
    pass