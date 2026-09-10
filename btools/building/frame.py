import bmesh
from bmesh.types import BMFace

from ..utils import extrude_face_region



def add_frame_depth(
    bm, door_faces, window_faces, arch_faces, frame_faces, depth, normal
):
    """Add depth to frame"""
    if depth != 0.0:
        all_faces = door_faces + window_faces + arch_faces + frame_faces

        def hash_face(f):
            face_hash = hash(
                (
                    f.calc_perimeter(),
                    f.calc_area(),
                    f.calc_center_median().to_tuple(4),
                )
            )
            return face_hash

        def hash_face_after(f):
            face_hash = hash(
                (
                    f.calc_perimeter(),
                    f.calc_area(),
                    (f.calc_center_median() + normal * depth).to_tuple(4),
                )
            )
            return face_hash

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
        else:
            return (
                new_door_faces,
                new_window_faces,
                new_arch_faces,
                new_frame_faces,
            )
    else:
        return door_faces, window_faces, arch_faces, frame_faces


def add_sill(
    bm, frame_faces, wall_normal,
    projection=0.075,
):
    """Protruding sill below the bottom frame member with a drip edge.

    Extends the lowest frame piece outward past the wall face and down to
    close against the wall. `wall_normal` points outward (away from the
    building interior).
    """
    from ..building.materialgroup import add_faces_to_group

    # -- find the bottom frame face (lowest median z)
    bottom = min(frame_faces, key=lambda f: f.calc_center_median().z)
    bottom_edge = max(
        bottom.edges, key=lambda e: (e.verts[0].co - e.verts[1].co).length
    )

    # -- extrude the bottom face outward past the wall + down
    offset = wall_normal * projection - (0, 0, thickness / 2)
    ret = bmesh.ops.extrude_face_region(bm, geom=[bottom])
    verts = [v for v in ret["geom"] if isinstance(v, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, verts=verts, vec=offset)

    # -- tag the sill faces
    sill_faces = [f for f in ret["geom"] if isinstance(f, BMFace)]
    if group is not None:
        add_faces_to_group(bm, sill_faces, group)
    return sill_faces


def add_threshold(
    bm, frame_faces, wall_normal, projection=0.03, height=0.015, group=None,
):
    """Low threshold member at the door opening base."""
    from ..building.materialgroup import add_faces_to_group

    bottom = min(frame_faces, key=lambda f: f.calc_center_median().z)
    ret = bmesh.ops.extrude_face_region(bm, geom=[bottom])
    verts = [v for v in ret["geom"] if isinstance(v, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, verts=verts, vec=wall_normal * projection)

    threshold_faces = [f for f in ret["geom"] if isinstance(f, BMFace)]
    if group is not None:
        add_faces_to_group(bm, threshold_faces, group)
    return threshold_faces


def add_casing(
    bm, opening_face, wall_normal, casing_width=0.06, casing_proud=0.015,
    group=None,
):
    """Decorative trim ring around an opening, proud of the wall face.

    `opening_face` is the wall face the element was cut into (before split).
    Creates an inset ring on the wall surface and extrudes it proud.
    """
    import bmesh as _bm

    res = _bm.ops.inset_individual(
        bm, faces=[opening_face], thickness=casing_width, use_even_offset=True
    )
    casing_ring = res.get("faces", [])
    if not casing_ring:
        return []

    ret = _bm.ops.extrude_face_region(bm, geom=casing_ring)
    verts = [v for v in ret["geom"] if isinstance(v, _bm.types.BMVert)]
    bm.ops.translate(
        bm, verts=verts, vec=wall_normal * casing_proud
    )

    casing_faces = [f for f in ret["geom"] if isinstance(f, BMFace)]
    if group is not None:
        add_faces_to_group(bm, casing_faces, group)
    return casing_faces
