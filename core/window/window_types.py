import bmesh
from ...utils import split
from ..fill import fill_bar, fill_louver, fill_glass_panes


def create_window(bm, faces, prop):
    """Generate a basic window

    Args:
        bm (bmesh.types.BMesh): bmesh for current edit mesh
        faces (bmesh.types.BMFace): current selected faces
        prop (bpy.types.PropertyGroup): WindowPropertyGroup
    """

    for face in faces:
        face = create_window_split(bm, face, prop.size_offset)
        if not face:
            continue

        face = create_window_frame(bm, face, prop)
        create_window_fill(bm, face, prop)


def create_window_split(bm, face, prop):
    """Use properties from SplitOffset to subdivide face into regular quads

    Args:
        bm (bmesh.types.BMesh): bmesh for current edit mesh
        face (bmesh.types.BMFace): face to make split (must be quad)
        prop (bpy.types.PropertyGroup): WindowPropertyGroup

    Returns:
        bmesh.types.BMFace: New face created after split
    """
    size, off = prop.size, prop.offset
    return split(bm, face, size.y, size.x, off.x, off.y, off.z)


def create_window_frame(bm, face, prop):
    """Create extrude and inset around a face to make window frame

    Args:
        bm (bmesh.types.BMesh): bmesh of current edit mesh
        face (bmesh.types.BMFace): face to make frame for
        prop (bpy.types.PropertyGroup): WindowPropertyGroup

    Returns:
        bmesh.types.BMFace: face after frame is created
    """
    face = bmesh.ops.extrude_discrete_faces(bm, faces=[face]).get("faces")[-1]
    bmesh.ops.translate(bm, verts=face.verts, vec=face.normal * prop.frame_depth / 2)

    if prop.frame_thickness > 0.0:
        bmesh.ops.inset_individual(bm, faces=[face], thickness=prop.frame_thickness)

    if prop.frame_depth > 0.0:
        f = bmesh.ops.extrude_discrete_faces(bm, faces=[face]).get("faces")[-1]
        bmesh.ops.translate(bm, verts=f.verts, vec=-f.normal * prop.frame_depth / 2)
        return f
    return face


def create_window_fill(bm, face, prop):
    """Create extra elements on face

    Args:
        bm (bmesh.types.BMesh): bmesh for current edit mesh
        face (bmesh.types.BMFace): face to operate on
        prop (bpy.types.PropertyGroup): WindowPropertyGroup
    """

    if prop.fill_type == "NONE":
        pass
    elif prop.fill_type == "GLASS PANES":
        fill_glass_panes(bm, face, prop.glass_fill)
    elif prop.fill_type == "BAR":
        fill_bar(bm, face, prop.bar_fill)
    elif prop.fill_type == "LOUVER":
        fill_louver(bm, face, prop.louver_fill)
