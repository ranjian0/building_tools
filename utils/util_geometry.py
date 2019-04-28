import bmesh
from mathutils import Matrix

def cube(bm, width=2, length=2, height=2):
    """ Create a cube in the given bmesh"""

    sc_x = Matrix.Scale(width, 4, (1, 0, 0))
    sc_y = Matrix.Scale(length, 4, (0, 1, 0))
    sc_z = Matrix.Scale(height, 4, (0, 0, 1))
    mat = sc_x @ sc_y @ sc_z
    ret = bmesh.ops.create_cube(bm, size=1, matrix=mat)
    return ret

def plane(bm, width=2, length=2):
    """ Create a plane in the given bmesh"""

    sc_x = Matrix.Scale(width, 4, (1, 0, 0))
    sc_y = Matrix.Scale(length, 4, (0, 1, 0))
    mat = sc_x @ sc_y
    ret = bmesh.ops.create_grid(
        bm, x_segments=1, y_segments=1, size=1, matrix=mat)
    return ret

def circle(bm, radius=1, segs=10, cap_tris=False):
    """ Create circle in the bmesh """
    ret = bmesh.ops.create_circle(
        bm, cap_ends=True, cap_tris=cap_tris, segments=segs, radius=radius)
    return ret

def cone(bm, r1=.5, r2=.01, height=2, segs=32):
    """ Create a cone in the bmesh """
    ret = bmesh.ops.create_cone(bm, diameter1=r1*2, diameter2=r2*2, depth=height,
                                cap_ends=True, cap_tris=True, segments=segs)
    return ret

def cylinder(bm, radius=1, height=2, segs=10):
    """ Create cylinder in bmesh """

    # -- circle
    ret = bmesh.ops.create_circle(bm,
        cap_ends=True, cap_tris=False, segments=segs, diameter=radius * 2)

    verts = ret['verts']
    face = list(verts[0].link_faces)

    res = bmesh.ops.extrude_discrete_faces(bm, faces=face)
    bmesh.ops.translate(bm, verts=res['faces'][-1].verts, vec=(0, 0, height))

    result = {'verts' : verts + list(res['faces'][-1].verts)}
    bmesh.ops.translate(bm, verts=result['verts'], vec=(0, 0, -height/2))
    return result

