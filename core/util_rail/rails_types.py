import bmesh
import itertools as it
from mathutils import Vector

from bmesh.types import BMVert
from ...utils import (
    cube,
    filter_geom,
    face_with_verts,
    calc_edge_median
    )

def make_railing(bm, edges, pw, ph, pd, rw, rh, rd, ww, wh, cpw, cph, hcp, df, fill, **kwargs):
    """Creates rails and posts along selected edges

    Args:
        bm    (bmesh.types.BMesh): bmesh of current edit mesh
        edges (list): list of edges to create rails along
        *args: items from RailsProperty, see rail_props.py
        **kwargs: Extra kwargs
    """

    for e in edges:
        lfaces = list({f for f in e.link_faces})
        if len(lfaces) > 1:
            lfaces = list(filter(lambda f: f.normal.z, lfaces))
        ref = lfaces[0].calc_center_median()
        cen = calc_edge_median(e)
        off_x = -pw / 4 if cen.x > ref.x else pw / 4
        off_y = -pw / 4 if cen.y > ref.y else pw / 4

        if hcp:
            for v in e.verts:
                off_x = -cpw / 2 if v.co.x > ref.x else cpw / 2
                off_y = -cpw / 2 if v.co.y > ref.y else cpw / 2
                pos = (v.co.x + off_x, v.co.y + off_y, v.co.z + (cph / 2))

                corner_post = create_post(bm, (cpw, cpw, cph), pos)
                del_faces(bm, corner_post)

                # Top decor
                px, py, pz = pos
                post_decor = create_post(bm, (cpw * 2, cpw * 2, cpw / 2), (px, py, v.co.z + cph + cpw / 4))

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
            create_rail(bm, e, cen, off_x, off_y, rw, rh, cph, cpw)

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
                size = (ww, e.calc_length() - (cpw * 2), wh)
                pos = cen.x + off_x, cen.y, cen.z + cph / 2
                darg = (True,) * 2 + (False,) * 2 + (True,) * 2
            else:
                size = (e.calc_length() - (cpw * 2), ww, wh)
                pos = cen.x, cen.y + off_y, cen.z + cph / 2
                darg = (True,) * 4 + (False,) * 2

            wall = create_post(bm, size, pos)
            if df:
                if wh < cph:
                    darg = (False, False) + darg[2:]
                del_faces(bm, wall, *darg)

    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=0.0)

def create_rail(bm, e, cen, off_x, off_y, rw, rh, cph, cpw):
    """ Create rail on top of posts """
    if len(set([v.co.x for v in e.verts])) == 1:
        size = (rw, e.calc_length() - (cpw * 3), rh)
        pos  = cen.x + off_x, cen.y, cen.z + cph + rh / 2
        darg = (False,) * 4 + (True,) * 2
    else:
        size = (e.calc_length() - (cpw * 3), rw, rh)
        pos  = cen.x, cen.y + off_y, cen.z + cph + rh / 2
        darg = (False,) * 2 + (True,) * 2 + (False,) * 2

    rail = create_post(bm, size, pos)
    del_faces(bm, rail, *darg)

def create_post(bm, size, position):
    """ Create cube to represent railing posts """
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

