import bmesh
from math import sin, cos
from mathutils import Vector, Matrix


def create_road(bm, prop):
    """Creates the original vertices
    """

    shoulder_width = sin(prop.shoulder_angle) * prop.shoulder_height
    shoulder_height = cos(prop.shoulder_angle) * prop.shoulder_height
    total_width_left = prop.width / 2
    total_width_right = 0

    if prop.generate_shoulders:
        total_width_left += prop.shoulder_width

    total_width_right = total_width_left
    if prop.generate_left_sidewalk:
        total_width_left += prop.sidewalk_width
    if prop.generate_right_sidewalk:
        total_width_right += prop.sidewalk_width

    # Left to right
    # Left shoulder down
    if not prop.generate_left_sidewalk and prop.generate_shoulders:
        bm.verts.new(Vector((-total_width_left - shoulder_width, 0, -shoulder_height)))

    # Left sidewalk top
    if prop.generate_left_sidewalk:
        bm.verts.new(Vector((-total_width_left, 0, prop.sidewalk_height)))

    # Left shoulder
    if prop.generate_shoulders:
        if prop.generate_left_sidewalk:
            bm.verts.new(Vector((-prop.width / 2 - prop.shoulder_width, 0, prop.sidewalk_height)))

        bm.verts.new(Vector((-prop.width / 2 - prop.shoulder_width, 0, 0)))
    else:
        bm.verts.new(Vector((-prop.width / 2, 0, 0)))

    # Main road
    bm.verts.new(Vector((-prop.width / 2, 0, 0)))
    bm.verts.new(Vector((prop.width / 2, 0, 0)))
    
    # Right shoulder
    if prop.generate_shoulders:
        bm.verts.new(Vector((prop.width / 2 + prop.shoulder_width, 0, 0)))

        if prop.generate_right_sidewalk:
            bm.verts.new(Vector((prop.width / 2 + prop.shoulder_width, 0, prop.sidewalk_height)))
    else:
        bm.verts.new(Vector((prop.width / 2, 0, 0)))

    # Left sidewalk top
    if prop.generate_right_sidewalk:
        bm.verts.new(Vector((total_width_right, 0, prop.sidewalk_height)))

    # Left shoulder down
    if not prop.generate_right_sidewalk and prop.generate_shoulders:
        bm.verts.new(Vector((total_width_right + shoulder_width, 0, -shoulder_height)))

    # Generate edges
    bm.verts.ensure_lookup_table()
    for i in range(len(bm.verts) - 1):
        bm.edges.new((bm.verts[i], bm.verts[i + 1]))


def continuous_extrude(bm, context, prop, edges, times):
    """ Extrudes road straight
    """
    original_times = times

    while times > 0:
        geom = bmesh.ops.extrude_face_region(bm, geom=edges)
        verts = [e for e in geom['geom'] if isinstance(e, bmesh.types.BMVert)]
        edges = [e for e in geom['geom'] if isinstance(e, bmesh.types.BMEdge)]

        interval = prop.interval
        if times == 1:
            interval = min(interval, prop.length - (original_times - 1) * interval)

        bmesh.ops.transform(bm, matrix=Matrix.Translation((0, interval, 0)), space=context.object.matrix_world, verts=verts)
        times -= 1
