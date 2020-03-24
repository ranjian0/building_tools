import bmesh
from ...utils import (
    filter_geom,
    extrude_face_region,
)


def add_frame_depth(bm, frame_faces, depth, normal):
    """ Add depth to frame
    """
    if depth > 0.0:
        return extrude_face_region(bm, frame_faces, depth, normal)
    else:
        return frame_faces, []
