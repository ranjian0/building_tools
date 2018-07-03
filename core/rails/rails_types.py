import math
import bmesh
import itertools as it

from math import copysign
from mathutils import Vector, Matrix

from bmesh.types import BMVert, BMEdge, BMFace
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

    def __init__(self):
        # -- global state {Wall FILL}
        self.wall_switch = False
        self.corner_angle = 0
        self.num_corners = 1

        # -- global state {remove colinear}
        self.colinear_loops = []

    def from_selection(self, bm, **kwargs):
        """ Creates railing from user selection """
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

        self.make_railing(bm, edges, lfaces, **kwargs)
        bmcopy.free()

    def from_edges(self, bm, edges, **kwargs):
        """ Create railing from edges """
        verts = list({v for e in edges for v in e.verts})
        lfaces = list({f for v in verts for f in v.link_faces if f.normal.z})
        lfaces = [f for f in lfaces if all([e in f.edges for e in edges])]

        self.make_railing(bm, edges, lfaces, **kwargs)

    def from_step_edges(self, bm, edges, normal, direction,
        cpw, cph, has_decor, fill,
        pd, ps, rs, **kwargs):
        """ Create railing from stair step edges """
        verts = list({v for e in edges for v in e.verts})
        lfaces = list({f for v in verts for f in v.link_faces if f.normal.z})

        # - find lowest edges
        min_edge = min(edges, key=lambda e: calc_edge_median(e).z)
        low_edges = [e for e in edges
            if round(calc_edge_median(e).z,3) == round(calc_edge_median(min_edge).z,3)]

        # -- add corner post
        for e in low_edges:
            loop = [l for l in e.link_loops if l.face in lfaces][-1]
            cen = calc_edge_median(e)
            tan = e.calc_tangent(loop)
            off = tan * cpw/2
            pos = cen + off + Vector((0, 0, cph/2))


            post = create_cube(bm, (cpw, cpw, cph), pos)

            del_faces(bm, post, bottom=True, top=has_decor)
            if has_decor:
                px, py, pz = pos
                _ = create_cube(bm, (cpw * 2, cpw * 2, cpw / 2), (px, py, pz + cph/2 + cpw / 4))

        # -- add fill types
        if fill == 'POSTS':
            other_edges = list(set(edges) - set(low_edges))
            # -- add mid posts
            for e in other_edges:
                loop = [l for l in e.link_loops if l.face in lfaces][-1]
                cen = calc_edge_median(e)
                tan = e.calc_tangent(loop)
                off = tan * cpw/2
                pos = cen + off + Vector((0, 0, cph/2 - rs/2))

                post = create_cube(bm, (ps, ps, cph-rs), pos)

            # -- add rail
            rail_groups = []
            if direction == 'FRONT':
                ledges = edges[:int(len(edges)/2)]
                redges = edges[int(len(edges)/2):]
                rail_groups.append(ledges)
                rail_groups.append(redges)
            else:
                rail_groups.append(edges)

            for group in rail_groups:
                cen = calc_verts_median([v for e in group for v in e.verts])
                off = Vector((0, 0, cph))
                pos = cen + off

                length = sum([e.calc_length() for e in group])
                size = (length, 2*rs, rs)

                rail = cube(bm, *size)
                bmesh.ops.translate(bm, vec=pos, verts=rail['verts'])
                del_faces(bm, rail, right=True)

                # --rotate
                bmesh.ops.rotate(bm, verts=rail['verts'],
                    cent=calc_verts_median(rail['verts']),
                    matrix=Matrix.Rotation(math.atan2(normal.y, normal.x), 4, 'Z'))


        elif fill == 'RAILS':
            pass
        elif fill == 'WALL':
            pass


    def make_railing(self, bm, edges, lfaces, remove_colinear, **kwargs):
        """Creates rails and posts along selected edges

        Args:
            bm    (bmesh.types.BMesh): bmesh of current edit mesh
            edges (list): list of edges to create rails along
            *args: items from RailsProperty, see rail_props.py
            **kwargs: Extra kwargs
        """

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
            # - remove loops where edges are parallel, and both link_edges are in selection
            flt_parallel = lambda loop: round(loop.calc_angle(),3) == 3.142
            flt_mid = lambda loop: loop.link_loop_next in loops and loop.link_loop_prev in loops

            self.colinear_loops.extend([l for l in loops if (flt_parallel(l) and flt_mid(l))])
            loops = [l for l in loops if not (flt_parallel(l) and flt_mid(l))]

        self.make_corner_post(bm, loops, **kwargs)
        self.make_fill(bm, edges, **kwargs)
        bmesh.ops.remove_doubles(bm, verts=bm.verts)

    def make_corner_post(self, bm, loops, cpw, cph, has_decor, **kwargs):
        """ Create Corner posts """
        num_poly = lambda ang: round((2*math.pi) / (math.pi - ang))
        for loop in loops:
            v = loop.vert
            e = loop.edge

            vec = loop.calc_tangent()
            off = vec * math.sqrt(2 * ((cpw/2)**2))
            pos = v.co + off + Vector((0, 0, cph/2))

            angle = loop.calc_angle()
            segments = num_poly(angle)
            if segments == 4 or segments < 0: # - (90 or 180)
                post = create_cube(bm, (cpw, cpw, cph), pos)

                del_faces(bm, post, bottom=True, top=has_decor)
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

            # -- align
            v1, v2 = e.verts
            dx, dy = (v1.co - v2.co).normalized().xy
            bmesh.ops.rotate(bm, verts=post['verts'],
                cent=calc_verts_median(post['verts']),
                matrix=Matrix.Rotation(math.atan2(dy, dx), 4, 'Z'))

    def make_fill(self, bm, edges, fill, **kwargs):
        """ Create fill types for railing """
        for edge in edges:
            if fill == 'RAILS':
                self.make_fill_rails(bm, edge, **kwargs)
            elif fill == 'POSTS':
                self.make_fill_posts(bm, edge, **kwargs)
            elif fill == 'WALL':
                self.make_fill_walls(bm, edge, **kwargs)

    def make_fill_rails(self, bm, edge, cpw, cph, rd, rs, expand, **kwargs):
        v1, v2 = edge.verts
        dx, dy = (v1.co - v2.co).normalized().xy
        tan = edge_tangent(edge)

        off = tan.normalized() * (cpw/2)
        start = calc_edge_median(edge) + off
        stop = calc_edge_median(edge) + off + Vector((0, 0, cph))
        if expand:
            size = (edge.calc_length(), rs, rs)
        else:
            size = (edge.calc_length() - (cpw * 2), rs, rs)

        rail = cube(bm, *size)
        del_faces(bm, rail, left=True, right=True)

        bmesh.ops.rotate(bm, verts=rail['verts'],
            cent=calc_verts_median(rail['verts']),
            matrix=Matrix.Rotation(math.atan2(dy, dx), 4, 'Z'))

        rail_count = int((cph / rs) * rd)
        array_elements(bm, rail, rail_count, start, stop)

    def make_fill_posts(self, bm, edge, cpw, cph, pd, ps, rs, **kwargs):
        v1, v2 = edge.verts
        vec = (v1.co - v2.co).normalized()
        tan = edge_tangent(edge).normalized()

        # -- add posts
        off = tan * (cpw/2)
        gap = vec * cpw
        start = v1.co + off + Vector((0, 0, cph/2 - rs/2)) - gap
        stop = v2.co + off + Vector((0, 0, cph/2 - rs/2)) + gap
        size = (ps, ps, cph-rs)

        post = cube(bm, *size)
        del_faces(bm, post, top=True, bottom=True)

        bmesh.ops.rotate(bm, verts=post['verts'],
            cent=calc_verts_median(post['verts']),
            matrix=Matrix.Rotation(math.atan2(*vec.yx), 4, 'Z'))

        post_count = int((edge.calc_length() / ps) * pd)
        array_elements(bm, post, post_count, start, stop)

        # fill gaps created by remove colinear
        if self.colinear_loops:
            # -- fill spaces created by no corner posts
            for loop in self.colinear_loops:
                if loop.edge != edge:
                    continue

                v = loop.vert
                p = v.co + off + Vector((0, 0, cph/2 - rs/2))
                fill_post = create_cube(bm, size, p)
                del_faces(bm, fill_post, top=True, bottom=True)

        # -- add top rail
        pinch = 0.01 # offset to prevent z-buffer fighting
        rail_pos = calc_edge_median(edge) + off + Vector((0, 0, cph - rs/2 - pinch))
        size = (edge.calc_length(), 2*rs, rs)

        rail = create_cube(bm, size, rail_pos)
        del_faces(bm, rail, left=True, right=True)

        bmesh.ops.rotate(bm, verts=rail['verts'],
            cent=calc_verts_median(rail['verts']),
            matrix=Matrix.Rotation(math.atan2(*vec.yx), 4, 'Z'))

    def make_fill_walls(self, bm, edge, cph, cpw, ww, expand, **kwargs):
        off = cpw
        if self.wall_switch:
            # - a cylinder corner post was created, determine length of side with cosine rule
            val_a = 2 * (cpw**2)
            val_b = val_a * math.cos(self.corner_angle)
            off = math.sqrt(val_a - val_b)

        v1, v2 = edge.verts
        _dir = (v1.co - v2.co).normalized()
        tan = edge_tangent(edge)

        if self.wall_switch: # -- only for cyliner corner posts
            start = v1.co - (_dir * off)
            end   = v2.co + (_dir * off)
        else:
            if expand:
                start = v1.co
                end   = v2.co
            else:
                start = v1.co - (_dir * off)
                end   = v2.co + (_dir * off)

        create_wall(bm, start, end, cph, ww, tan)

def edge_tangent(edge):
    tan = None
    for l in edge.link_loops:
        t = edge.calc_tangent(l)
        if not round(t.z):
            tan = t
    return tan

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

        # delete hidden geom
        edges = filter_geom(res['geom'], BMEdge)
        faces = [f for e in edges for f in e.link_faces
                    if not f.normal.z and f not in filter_geom(res['geom'], BMFace)]
        bmesh.ops.delete(bm, geom=faces, context=3)

def del_faces(bm, post, top=False, bottom=False, left=False, right=False, front=False, back=False):
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
