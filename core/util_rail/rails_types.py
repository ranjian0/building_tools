import math
import time
import bmesh
import itertools as it

from copy import copy
from math import copysign
from mathutils import Vector, Matrix

from bmesh.types import BMVert
from ...utils import (
    cube,
    plane,
    select,
    filter_geom,
    face_with_verts,
    calc_edge_median,
    calc_verts_median,
    )


def make_railing(bm, remove_colinear, **kwargs):
    """Creates rails and posts along selected edges

    Args:
        bm    (bmesh.types.BMesh): bmesh of current edit mesh
        edges (list): list of edges to create rails along
        *args: items from RailsProperty, see rail_props.py
        **kwargs: Extra kwargs
    """

    lfaces = []
    bmcopy = bm.copy()
    edges = [e for e in bmcopy.edges if e.select]
    if edges:
        # -- if user selection is edges
        lfaces = list({f for e in edges for f in e.link_faces if f.normal.z})
    else:
        sel_faces = [f for f in bmcopy.faces if f.select]
        lfaces = sel_faces
        if sel_faces:
            # -- if user selection if faces
            all_edges = list({e for f in sel_faces for e in f.edges})
            edges = [e for e in all_edges
                if len(list({f for f in e.link_faces if f in sel_faces})) == 1]
    bmesh.ops.dissolve_faces(bmcopy, faces=lfaces)

    loops = list({loop for e in edges for loop in e.link_loops})
    if remove_colinear:
        # - remove loops where edges are parallel
        loops = [l for l in loops if round(l.calc_angle(),3) != 3.142]

    make_corner_post(bm, loops, **kwargs)
    bmcopy.free()



def make_corner_post(bm, loops, cpw, cph, has_decor, **kwargs):
    """ Create Corner posts """
    for loop in loops:
        v = loop.vert

        vec = loop.calc_tangent()
        off_x = math.copysign(cpw/2, vec.x)
        off_y = math.copysign(cpw/2, vec.y)
        pos = (v.co.x + off_x, v.co.y + off_y, v.co.z + (cph / 2))

        post = create_cube(bm, (cpw, cpw, cph), pos)
        del_faces(bm, post, top=has_decor)
        if has_decor:
            px, py, pz = pos
            _ = create_cube(bm, (cpw * 2, cpw * 2, cpw / 2), (px, py, pz + cph/2 + cpw / 4))



'''
def make_railing(bm, edges, pw, ph, pd, rw, rh, rd, ww, cpw, cph, hcp, fill, has_decor, **kwargs):
    """Creates rails and posts along selected edges

    Args:
        bm    (bmesh.types.BMesh): bmesh of current edit mesh
        edges (list): list of edges to create rails along
        *args: items from RailsProperty, see rail_props.py
        **kwargs: Extra kwargs
    """

    # calculate reference from face(s)
    lfaces = list({f for e in edges for f in e.link_faces if f.normal.z})
    ref = calc_verts_median(list({v for f in lfaces for v in f.verts}))

    # merge colinear edges into single edge
    # new_bm = merge_colinear_edges(edges)
    # edges = list(new_bm.edges)


    # Create Corner posts
    # -- required by all types
    verts = list({vert for e in edges for vert in e.verts})
    angles = list([ref.angle(v.co) for v in verts])
    vsorted = sorted(verts, key=lambda v:angles[verts.index(v)])

    for v in {vert for e in edges for vert in e.verts}:
        link_edges = list({e for e in v.link_edges
                    for vert in e.verts if vert != v and vert.co.z == v.co.z})
        link_verts = [e.other_vert(v) for e in link_edges]

        vec = calc_verts_median(link_verts)
        off_x = -cpw / 2 if v.co.x > vec.x else cpw / 2
        off_y = -cpw / 2 if v.co.y > vec.y else cpw / 2

        _cph = cph if has_decor else cph + rh
        pos = (v.co.x + off_x, v.co.y + off_y, v.co.z + (_cph / 2))

        corner_post(bm, (cpw, cpw, _cph), pos, has_decor)

    for e in edges:
        cen = calc_edge_median(e)
        off_x = -pw / 4 if cen.x > ref.x else pw / 4
        off_y = -pw / 4 if cen.y > ref.y else pw / 4

        if fill == 'RAILS':  # has_rails:
            num_rails = int((cph / rh) * rd)
            if len(set([v.co.x for v in e.verts])) == 1:
                size = (cpw / 2, e.calc_length() - (cpw * 2), rh)
                st = Vector((cen.x + off_x, cen.y, cen.z))
                sp = Vector((cen.x + off_x, cen.y, cen.z + cph))
            else:
                size = (e.calc_length() - (cpw * 2), cpw / 2, rh)
                st = Vector((cen.x, cen.y + off_y, cen.z))
                sp = Vector((cen.x, cen.y + off_y, cen.z + cph))

            rail = cube(bm, *size)
            array_elements(bm, rail, num_rails, st, sp)

        elif fill == 'POSTS':  # has_mid_posts:
            # create top rail
            create_rail(bm, e, cen, off_x, off_y, rw, rh, cph, cpw, has_decor)

            # create posts
            num_posts = int((e.calc_length() / (pw * 2)) * pd)
            st, sp = [v.co for v in e.verts]
            if st.x == sp.x:
                start = Vector((st.x + off_x, st.y, st.z + ph / 2))
                stop = Vector((sp.x + off_x, sp.y, sp.z + ph / 2))
            else:
                start = Vector((st.x, st.y + off_y, st.z + ph / 2))
                stop = Vector((sp.x, sp.y + off_y, sp.z + ph / 2))

            post = cube(bm, pw / 2, pw / 2, ph)
            del_faces(bm, post)
            array_elements(bm, post, num_posts, start, stop)

        elif fill == 'WALL':  # has_wall:
            # create top rail
            create_rail(bm, e, cen, off_x, off_y, rw, rh, cph, cpw)

            # create wall
            if len(set([v.co.x for v in e.verts])) == 1:
                pos = cen.x + off_x, cen.y, cen.z + cph / 2
                rot = 90 if ref.x < cen.x else -90
                length = e.calc_length() - (cpw * 2)
                width = cph
                axis = 'Y'
            else:
                pos = cen.x, cen.y + off_y, cen.z + cph / 2
                rot = -90 if ref.y < cen.y else 90
                width = e.calc_length() - (cpw * 2)
                length = cph
                axis = 'X'

            wall = plane(bm, width/2, length/2)
            bmesh.ops.translate(bm, verts=wall['verts'], vec=pos)
            bmesh.ops.rotate(bm, cent=pos, verts=wall['verts'],
                matrix=Matrix.Rotation(math.radians(rot), 4, axis))

    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=0.0)
'''

def create_rail(bm, e, cen, off_x, off_y, rw, rh, cph, cpw, has_decor=False):
    """ Create rail on top of posts """
    factor = 3 if has_decor else 2
    if len(set([v.co.x for v in e.verts])) == 1:
        size = (rw, e.calc_length() - (cpw * factor), rh)
        pos  = cen.x + off_x, cen.y, cen.z + cph + rh / 2
        darg = (False,) * 4 + (True,) * 2
    else:
        size = (e.calc_length() - (cpw * factor), rw, rh)
        pos  = cen.x, cen.y + off_y, cen.z + cph + rh / 2
        darg = (False,) * 2 + (True,) * 2 + (False,) * 2

    rail = create_cube(bm, size, pos)
    del_faces(bm, rail, *darg)

def create_cube(bm, size, position):
    """ Create cube with size and at position"""
    post = cube(bm, *size)
    bmesh.ops.translate(bm, verts=post['verts'], vec=position)
    return post


def del_faces(bm, post, top=True, bottom=True, left=False, right=False, front=False, back=False):
    """ Delete flagged faces for the given post (cube geometry) """
    vts = post['verts']
    keys = ['z', 'z', 'x', 'x', 'y', 'y']
    dirs = [top, bottom, left, right, front, back]
    slcs = it.chain.from_iterable(it.repeat([slice(4,8), slice(4)], 3))

    faces = []
    for direction, key, _slice in zip(dirs, keys, slcs):
        if direction:
            vts.sort(key=lambda v: getattr(v.co, key))
            faces.append(face_with_verts(bm, vts[_slice]))

    bmesh.ops.delete(bm, geom=faces, context=3)

def array_elements(bm, elem, count, start, stop):
    """ Duplicate elements count-1 times between start and stop """
    dx = (stop.x - start.x) / (count + 1)
    dy = (stop.y - start.y) / (count + 1)
    dz = (stop.z - start.z) / (count + 1)

    for i in range(count):
        if i == 0:
            px, py, pz = start.x + dx, start.y + dy, start.z + dz
            bmesh.ops.translate(bm, verts=elem['verts'], vec=(px, py, pz))
        else:
            faces = list({f for v in elem['verts'] for f in v.link_faces})
            ret = bmesh.ops.duplicate(bm, geom=faces)
            bmesh.ops.translate(bm, verts=filter_geom(ret['geom'], BMVert), vec=(dx * i, dy * i, dz * i))

'''
def edge_slope(e):
    """ Calculate the slope of an edge """
    p1, p2 = [v.co for v in e.verts]
    if (p2.x - p1.x) == 0:
        return None # infinite
    return (p2.y - p1.y) / (p2.x - p1.x)

def colinear(e1, e2):
    """ Determine whether e1 and e2 are colinear """
    cen1, cen2 = calc_edge_median(e1), calc_edge_median(e2)

    if edge_slope(e1) == edge_slope(e2):
        # -- now make sure edges have common vert
        vts1, vts2 = {v for v in e1.verts}, {v for v in e2.verts}
        if len(vts1 & vts2) == 1:
            return True
    return False

def get_bounding_verts(edges):
    """ Determine furmost verts for given edges """
    verts = list({v for e in edges for v in e.verts})

    # if len(set([v.co.x for v in verts])) == 1:
    #     return [
    #         min(verts, key=lambda v:v.co.y),
    #         max(verts, key=lambda v:v.co.y)
    #     ]

    # elif len(set([v.co.y for v in verts])) == 1:
    #     return [
    #         min(verts, key=lambda v:v.co.x),
    #         max(verts, key=lambda v:v.co.x)
    #     ]
    # else:
    verts.sort(key=lambda v:v.co.x)
    verts.sort(key=lambda v:v.co.y)
    return [verts[0], verts[-1]]

def merge_colinear_edges(edges):
    """ Convert all colinear edge groups into single edge """

    tmp_bm = bmesh.new()
    col_edge_groups = []

    while len(edges):
        group = []

        current  = edges[0]
        group.append(current)

        for e in edges:
            if e != current and colinear(e, current):
                group.append(e)

        for e in group:
            edges.remove(e)

        col_edge_groups.append(group)

    for group in col_edge_groups:
        if len(group) > 1:
            bound_verts = get_bounding_verts(group)
            verts = [tmp_bm.verts.new(v.co) for v in bound_verts]
            tmp_bm.edges.new(verts)
        elif len(group) == 1:
            verts = [tmp_bm.verts.new(v.co) for v in group[-1].verts]
            tmp_bm.edges.new(verts)

    return tmp_bm
'''