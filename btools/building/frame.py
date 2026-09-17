import math

import bmesh
from bmesh.types import BMFace, BMVert
from mathutils import Matrix

from ..utils import extrude_face_region, local_xyz
from .materialgroup import MaterialGroup, add_faces_to_group


def add_sill(bm, frame_faces, wall_normal, projection=0.075):
    """Protruding sill below the bottom frame member.

    Extends the lowest frame piece outward past the wall face.
    wall_normal points out of the wall (toward the viewer).
    """
    frame_faces = [f for f in frame_faces if f.is_valid]
    if not frame_faces:
        return []
    bottom = min(frame_faces, key=lambda f: f.calc_center_median().z)
    offset = wall_normal * projection
    ret = bmesh.ops.extrude_face_region(bm, geom=[bottom])
    verts = [v for v in ret["geom"] if isinstance(v, BMVert)]
    bmesh.ops.translate(bm, verts=verts, vec=offset)
    faces = [f for f in ret["geom"] if isinstance(f, BMFace)]
    add_faces_to_group(bm, faces, MaterialGroup.FRAME)
    return faces


def add_threshold(bm, frame_faces, wall_normal, projection=0.03):
    """Low threshold member at the door opening base."""
    frame_faces = [f for f in frame_faces if f.is_valid]
    if not frame_faces:
        return []
    bottom = min(frame_faces, key=lambda f: f.calc_center_median().z)
    offset = wall_normal * projection
    ret = bmesh.ops.extrude_face_region(bm, geom=[bottom])
    verts = [v for v in ret["geom"] if isinstance(v, BMVert)]
    bmesh.ops.translate(bm, verts=verts, vec=offset)
    faces = [f for f in ret["geom"] if isinstance(f, BMFace)]
    add_faces_to_group(bm, faces, MaterialGroup.FRAME)
    return faces


def add_frame_depth(
    bm, door_faces, window_faces, arch_faces, frame_faces, depth, normal
):
    """Add depth to frame"""
    if depth != 0.0:
        all_faces = door_faces + window_faces + arch_faces + frame_faces

        # -- capture each face's expected resting position before the
        #    extrude; matching by (perimeter, area, center) hash loses
        #    faces to float32 rounding at the 4th decimal
        categories = [door_faces, window_faces, arch_faces, frame_faces]
        expected = [
            [f.calc_center_median() + normal * depth for f in faces]
            for faces in categories
        ]

        new_faces, surrounding_faces = extrude_face_region(
            bm, list(set(all_faces)), -depth, normal
        )

        # -- nearest-centroid matching: every face moved by the same
        #    offset, so each new face is closest to its own origin
        remaining = list(new_faces)
        matched = []
        for positions in expected:
            group = []
            for exp in positions:
                if not remaining:
                    break
                best = min(
                    remaining,
                    key=lambda nf: (nf.calc_center_median() - exp).length_squared,
                )
                remaining.remove(best)
                group.append(best)
            matched.append(group)

        new_door_faces, new_window_faces, new_arch_faces, new_frame_faces = matched

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


def bevel_frame(bm, frame_faces, width=0.003, exclude_faces=()):
    """Chamfer frame edges for a manufactured profile.

    exclude_faces: opening faces (door/window leaf) sharing inner frame
    edges — beveling those edges would rebuild the opening face and
    invalidate its reference.
    """
    excl_edges = {
        e for f in exclude_faces if f is not None and f.is_valid for e in f.edges
    }
    frame_edges = [e for f in frame_faces for e in f.edges if e not in excl_edges]
    bmesh.ops.bevel(
        bm,
        geom=list(set(frame_edges)),
        offset=width,
        offset_type="OFFSET",
        segments=1,
        profile=0.5,
        affect="EDGES",
        clamp_overlap=True,
    )


def add_casing(bm, frame_faces, wall_normal, casing_width=0.06, casing_depth=0.015):
    """Raised trim ring on the wall surface around the opening.

    wall_normal points out of the wall (toward the viewer); the casing
    extends along it. Only boundary faces lying exactly in the wall plane
    are extruded — the recessed opening face is excluded.
    """
    # -- wall-surface distance: the outermost frame verts lie in the wall plane
    plane_d = max(v.co.dot(wall_normal) for f in frame_faces for v in f.verts)

    # -- find frame boundary faces coplanar with the wall surface
    frame_idx = set(f.index for f in frame_faces)
    boundary_faces = set()
    for f in frame_faces:
        for e in f.edges:
            for nf in e.link_faces:
                if nf.index in frame_idx:
                    continue
                if abs(nf.calc_center_median().dot(wall_normal) - plane_d) < 1e-4:
                    boundary_faces.add(nf)

    if not boundary_faces:
        return []

    # -- extrude the wall strips proud of the wall
    ret = bmesh.ops.extrude_face_region(bm, geom=list(boundary_faces))
    verts = [v for v in ret["geom"] if isinstance(v, BMVert)]
    bmesh.ops.translate(bm, verts=verts, vec=wall_normal * casing_depth)
    faces = [f for f in ret["geom"] if isinstance(f, BMFace)]
    add_faces_to_group(bm, faces, MaterialGroup.FRAME)
    return faces


def add_hardware(
    bm,
    door_face,
    frame_faces,
    wall_normal,
    frame_thickness,
    handle_height=1.05,
    handle_style="LEVER",
):
    """Lever or bar-pull handle mounted on the door leaf.

    door_face anchors the leaf plane (the recessed face inside the frame);
    frame_faces anchor the opening extents for positioning along the wall.
    """
    xyz = local_xyz(door_face)
    x_axis, z_axis, n = xyz[0], xyz[1], xyz[2]

    # -- opening extents from the frame ring, leaf plane from the door face
    frame_xs = [v.co.dot(x_axis) for f in frame_faces for v in f.verts]
    frame_zs = [v.co.dot(z_axis) for f in frame_faces for v in f.verts]
    leaf_d = door_face.calc_center_median().dot(n)

    # -- latch position: measured from the OPENING edge (the frame ring's
    #    outer edge lies in the wall plane, frame_thickness outboard)
    opening_x = max(frame_xs) - frame_thickness
    latch_x = opening_x - 0.05  # 50mm in from the latch-side jamb face
    latch_z = min(frame_zs) + handle_height
    pos = x_axis * latch_x + z_axis * latch_z + n * leaf_d
    outward = n

    if handle_style == "BAR_PULL":
        # -- vertical bar pull (commercial style)
        bar_h = 0.3
        bar_w = 0.03
        bar_proud = 0.06

        ret = bmesh.ops.create_cube(
            bm,
            size=1.0,
            matrix=Matrix.Translation(pos + outward * (bar_proud / 2 + 0.005))
            @ Matrix.Scale(bar_w, 4, x_axis)
            @ Matrix.Scale(bar_proud, 4, outward)
            @ Matrix.Scale(bar_h, 4, z_axis),
        )
        _tag_new_faces(bm, ret, MaterialGroup.DOOR)
    else:
        # -- lever handle (residential style): rose disc + horizontal lever
        rose_r = 0.025
        rose_d = 0.008
        lever_l = 0.1
        lever_w = 0.015
        lever_proud = 0.025

        # -- rose (small disc on the door face)
        ret = bmesh.ops.create_cone(
            bm,
            cap_ends=True,
            segments=16,
            radius1=rose_r,
            radius2=rose_r,
            depth=rose_d,
            matrix=Matrix.Translation(pos + outward * (rose_d / 2))
            @ (Matrix.Rotation(math.pi / 2, 4, x_axis)),
        )
        _tag_new_faces(bm, ret, MaterialGroup.DOOR)

        # -- lever bar extending from the rose toward the door center
        lever_center = (
            pos
            + outward * (lever_proud / 2 + rose_d / 2)
            - x_axis * (lever_l / 2 - rose_r)
        )
        ret = bmesh.ops.create_cube(
            bm,
            size=1.0,
            matrix=Matrix.Translation(lever_center)
            @ Matrix.Scale(lever_l, 4, x_axis)
            @ Matrix.Scale(lever_w, 4, z_axis)
            @ Matrix.Scale(lever_proud, 4, outward),
        )
        _tag_new_faces(bm, ret, MaterialGroup.DOOR)


def _tag_new_faces(bm, ret, group):
    """Tag faces created by primitive ops that return verts, not geom."""
    faces = {f for v in ret.get("verts", []) for f in v.link_faces}
    add_faces_to_group(bm, list(faces), group)
