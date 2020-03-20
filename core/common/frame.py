import bmesh
from ...utils import (
    filter_geom,
)


def add_frame_depth(bm, frame_faces, depth, normal):
    """ Add depth to frame
    """
    if depth > 0.0:
        geom = bmesh.ops.extrude_face_region(bm, geom=frame_faces).get("geom")
        verts = filter_geom(geom, bmesh.types.BMVert)
        bmesh.ops.translate(bm, verts=verts, vec=normal * depth)