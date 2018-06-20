import math
import bmesh
import itertools as it

from math import copysign
from mathutils import Vector, Matrix

from bmesh.types import BMVert, BMFace
from ...utils import (
    cube,
    plane,
    select,
    cylinder,
    filter_geom,
    face_with_verts,
    calc_edge_median,
    calc_verts_median,
    )


class MakeRailing:

    def __init__(self, *args, **kwargs):
        # -- global state {Wall FILL}
        self.wall_switch = False
        self.corner_angle = 0
        self.num_corners = 1

        # -- execute from user selection
        self.make_railing(*args, **kwargs)

    @classmethod
    def from_edges(cls, bm, edges, **kwargs):
        pass

    @classmethod
    def from_faces(cls, bm, faces, **kwargs):
        pass

    def make_railing(self, bm, remove_colinear, **kwargs):
        """Creates rails and posts along selected edges

        Args:
            bm    (bmesh.types.BMesh): bmesh of current edit mesh
            edges (list): list of edges to create rails along
            *args: items from RailsProperty, see rail_props.py
            **kwargs: Extra kwargs
        """

        bmcopy = bm.copy()
        lfaces = [f for f in bmcopy.faces if f.select]
        if lfaces:
            # -- user selection if faces
            all_edges = list({e for f in lfaces for e in f.edges})
            edges = [e for e in all_edges
                if len(list({f for f in e.link_faces if f in lfaces})) == 1]
        else:
            # -- user selection is edges
            edges = [e for e in bmcopy.edges if e.select]
            verts = list({v for e in edges for v in e.verts})
            lfaces = list({f for v in verts for f in v.link_faces if f.normal.z})


        if len(lfaces) > 1:
            bmesh.ops.dissolve_faces(bmcopy, faces=lfaces)

        loops = []
        for e in edges:
            for v in e.verts:
                if len(v.link_loops) > 1:
                    # - make sure we add loop whose face is in lfaces
                    loops.extend([l for l in v.link_loops if l.face in lfaces])
                else:
                    loops.extend([l for l in v.link_loops])
        loops = list(set(loops))

        if remove_colinear:
            # TODO - make this work on loop with more than two links
            # - remove loops where edges are parallel, and both link_edges in selection
            flt_parallel = lambda loop: round(loop.calc_angle(),3) == 3.142
            flt_mid = lambda loop: loop.link_loop_next in loops and loop.link_loop_prev in loops

            loops = [l for l in loops if not (flt_parallel(l) and flt_mid(l))]


        self.make_corner_post(bm, loops, **kwargs)
        self.make_fill(bm, edges, **kwargs)
        bmesh.ops.remove_doubles(bm, verts=bm.verts)
        bmcopy.free()

    def make_corner_post(self, bm, loops, cpw, cph, has_decor, **kwargs):
        """ Create Corner posts """
        num_poly = lambda ang: round((2*math.pi) / (math.pi - ang))
        for loop in loops:
            v = loop.vert

            vec = loop.calc_tangent()
            off_x = math.copysign(cpw/2, vec.x)
            off_y = math.copysign(cpw/2, vec.y)
            pos = v.co + Vector((off_x, off_y, cph/2))

            angle = loop.calc_angle()
            segments = num_poly(angle)
            if segments == 4 or segments < 0: # - (90 or 180)
                post = create_cube(bm, (cpw, cpw, cph), pos)

                del_faces(bm, post, top=has_decor)
                if has_decor:
                    px, py, pz = pos
                    _ = create_cube(bm, (cpw * 2, cpw * 2, cpw / 2), (px, py, pz + cph/2 + cpw / 4))

            else:
                pos = v.co + (vec * cpw) + Vector((0, 0, cph/2))
                post = create_cylinder(bm, cpw/2, cph, segments, pos)

                # -- store global state
                self.wall_switch = True
                self.num_corners = segments
                self.corner_angle = math.pi - angle

    def make_fill(self, bm, edges, fill, **kwargs):
        """ Create fill types for railing """
        for edge in edges:
            if fill == 'RAILS':
                self.make_fill_rails(bm, edge, **kwargs)
            elif fill == 'POSTS':
                self.make_fill_posts(bm, edge, **kwargs)
            elif fill == 'WALL':
                self.make_fill_walls(bm, edge, **kwargs)

    def make_fill_rails(self, bm, edge, cpw, cph, rc, rs, **kwargs):
        v1, v2 = edge.verts
        dx, dy = (v1.co - v2.co).normalized().xy
        tan = edge_tangent(edge)

        off = tan.normalized() * (cpw/2)
        start = calc_edge_median(edge) + off
        stop = calc_edge_median(edge) + off + Vector((0, 0, cph))
        size = (edge.calc_length() - (cpw * 2), rs, rs)

        rail = cube(bm, *size)
        del_faces(bm, rail, left=True, right=True)

        bmesh.ops.rotate(bm, verts=rail['verts'],
            cent=calc_verts_median(rail['verts']),
            matrix=Matrix.Rotation(math.atan2(dy, dx), 4, 'Z'))
        array_elements(bm, rail, rc, start, stop)

    def make_fill_posts(self, bm, edge, **kwargs):
        pass

    def make_fill_walls(self, bm, edge, cph, cpw, ww, **kwargs):
        off = cpw
        if self.wall_switch:
            # - a cylinder corner post was created, determine length of side with cosine rule
            val_a = 2 * (cpw**2)
            val_b = val_a * math.cos(self.corner_angle)
            off = math.sqrt(val_a - val_b)

        v1, v2 = edge.verts
        _dir = (v1.co - v2.co).normalized()
        tan = edge_tangent(edge)

        start = v1.co - (_dir * off)
        end = v2.co + (_dir * off)
        create_wall(bm, start, end, cph, ww, tan)

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

'''

def edge_tangent(edge):
    tan = None
    for l in edge.link_loops:
        t = edge.calc_tangent(l)
        if not round(t.z):
            tan = t
    return tan

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

def create_cylinder(bm, r, h, segs, position):
    """ Create cylinder at pos"""
    cy = cylinder(bm, r, h, segs)
    bmesh.ops.translate(bm, verts=cy['verts'], vec=position)
    return cy

def create_wall(bm, start, end, height, width, tangent):
    """ Extrude a wall of height from start to end """
    start_v1 = bm.verts.new(start)
    start_v2 = bm.verts.new(start + Vector((0, 0, height)))
    start_edge = bm.edges.new((start_v1, start_v2))

    res = bmesh.ops.extrude_edge_only(bm, edges=[start_edge])
    bmesh.ops.translate(bm,
        vec=end-start,
        verts=filter_geom(res['geom'], BMVert))

    if width:
        face = filter_geom(res['geom'], BMFace)[-1]
        if face.normal.to_tuple(3) != tangent.to_tuple(3):
            face.normal_flip()
        n = face.normal

        res = bmesh.ops.extrude_face_region(bm, geom=[face])
        bmesh.ops.translate(bm,
            vec=-n*width,
            verts=filter_geom(res['geom'], BMVert))

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