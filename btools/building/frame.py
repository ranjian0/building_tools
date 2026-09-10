import bmesh
from bmesh.types import BMFace, BMVert

from ..utils import extrude_face_region


def add_sill(bm, frame_faces, wall_normal, projection=0.075):
    """Protruding sill below the bottom frame member.

    Extends the lowest frame piece outward past the wall face.
    wall_normal points into the opening (the recess direction).
    """
    bottom = min(frame_faces, key=lambda f: f.calc_center_median().z)
    offset = -wall_normal * projection
    ret = bmesh.ops.extrude_face_region(bm, geom=[bottom])
    verts = [v for v in ret["geom"] if isinstance(v, BMVert)]
    bmesh.ops.translate(bm, verts=verts, vec=offset)
    return [f for f in ret["geom"] if isinstance(f, BMFace)]


def add_threshold(bm, frame_faces, wall_normal, projection=0.03):
    """Low threshold member at the door opening base."""
    bottom = min(frame_faces, key=lambda f: f.calc_center_median().z)
    offset = -wall_normal * projection
    ret = bmesh.ops.extrude_face_region(bm, geom=[bottom])
    verts = [v for v in ret["geom"] if isinstance(v, BMVert)]
    bmesh.ops.translate(bm, verts=verts, vec=offset)
    return [f for f in ret["geom"] if isinstance(f, BMFace)]


def add_frame_depth(
    bm, door_faces, window_faces, arch_faces, frame_faces, depth, normal
):
    """Add depth to frame"""
    if depth != 0.0:
        all_faces = door_faces + window_faces + arch_faces + frame_faces

        def hash_face(f):
            return hash(
                (f.calc_perimeter(), f.calc_area(), f.calc_center_median().to_tuple(4))
            )

        def hash_face_after(f):
            return hash(
                (
                    f.calc_perimeter(),
                    f.calc_area(),
                    (f.calc_center_median() + normal * depth).to_tuple(4),
                )
            )

        door_hashes = list(map(hash_face, door_faces))
        window_hashes = list(map(hash_face, window_faces))
        arch_hashes = list(map(hash_face, arch_faces))
        frame_hashes = list(map(hash_face, frame_faces))

        all_faces, surrounding_faces = extrude_face_region(
            bm, list(set(all_faces)), -depth, normal
        )

        new_door_faces = [f for f in all_faces if hash_face_after(f) in door_hashes]
        new_window_faces = [f for f in all_faces if hash_face_after(f) in window_hashes]
        new_arch_faces = [f for f in all_faces if hash_face_after(f) in arch_hashes]
        new_frame_faces = [f for f in all_faces if hash_face_after(f) in frame_hashes]

        if depth < 0.0:
            return (
                new_door_faces,
                new_window_faces,
                new_arch_faces,
                new_frame_faces + surrounding_faces,
            )
        return (
            new_door_faces,
            new_window_faces,
            new_arch_faces,
            new_frame_faces,
        )
    return door_faces, window_faces, arch_faces, frame_faces
