import bpy
import bmesh
from bmesh.types import BMVert
from mathutils import Vector
from ...utils import (
        plane,
        circle,
        link_obj,
        condition,
        make_mesh,
        bm_to_obj,
        make_object,
        bm_from_obj,
        filter_geom,
        calc_edge_median,
        kwargs_from_props,
        filter_vertical_edges,
        filter_horizontal_edges,
    )


class Floorplan:

    @classmethod
    def build(cls, update=False, _obj=None):
        """ Build the floorplan from given properties """

        # -- create the floorplan object
        obj = condition(update, _obj, make_object('floorplan', make_mesh('fp_mesh')))
        building = obj.building

        # -- get bmesh representation of object
        bm = bm_from_obj(obj)

        # -- use properties to create geometry
        props = building.floorplan
        if props.type == 'RECTANGULAR':
            cls.make_rectangular(bm, **kwargs_from_props(props))
        elif props.type == 'CIRCULAR':
            cls.make_circular(bm, **kwargs_from_props(props))
        elif props.type == 'COMPOSITE':
            cls.make_composite(bm, **kwargs_from_props(props))
        elif props.type == 'H-SHAPED':
            cls.make_hshaped(bm, **kwargs_from_props(props))

        # -- write bmesh back into object
        bm_to_obj(bm, obj)

        # -- link object to current scene
        if not update:
            link_obj(obj)

    @classmethod
    def make_rectangular(cls, bm, width=1, length=2, **kwargs):
        """ Create a rectangular plane """
        plane(bm, width, length)

    @classmethod
    def make_circular(cls, bm, radius=1, segs=32, cap_tris=False, **kwargs):
        """ Create a circular plane """
        circle(bm, radius, segs, cap_tris)

    @classmethod
    def make_composite(cls, bm, width=2, length=2, tl=1, tl1=1, tl2=1, tl3=1, **kwargs):
        """ Create a square face whose sides are extruded """
        base = plane(bm, width, length)
        ref = list(bm.faces)[-1].calc_center_median()

        # Sort edges to make predictable winding
        edges = list(bm.edges)
        edges.sort(key=lambda ed: calc_edge_median(ed).x)
        edges.sort(key=lambda ed: calc_edge_median(ed).y)

        exts = [tl, tl1, tl2, tl3]
        for idx, e in enumerate(edges):
            if exts[idx] > 0:
                res = bmesh.ops.extrude_edge_only(bm, edges=[e])
                verts = filter_geom(res['geom'], BMVert)

                v = (calc_edge_median(e) - ref)
                v.normalize()
                bmesh.ops.translate(bm, verts=verts, vec=v * exts[idx])

    @classmethod
    def make_hshaped(cls, bm, width=2, length=2, tw=1, tl=1, tw1=1, tl1=1, tw2=1, tl2=1, tw3=1, tl3=1, **kwargs):
        """ Create a h-shaped flat plane """

        base = plane(bm, width, length)
        face = list(bm.faces)[-1]
        ref = face.calc_center_median()
        n = face.normal

        # make side extrusions
        for e in filter_vertical_edges(bm.edges, n):
            res = bmesh.ops.extrude_edge_only(bm, edges=[e])
            verts = filter_geom(res['geom'], BMVert)

            v = (calc_edge_median(e) - ref)
            v.normalize()

            bmesh.ops.translate(bm, verts=verts, vec=v)

        # Find all top edges and filter ones in the middle
        op_edges = filter_horizontal_edges(bm.edges, n)
        # --filter mid row
        op_edges.sort(key=lambda ed: calc_edge_median(ed).x)
        op_edges = op_edges[:2] + op_edges[4:]
        # -- make deterministic
        op_edges.sort(key=lambda ed: calc_edge_median(ed).y)
        lext = [tl, tl1, tl2, tl3]
        wext = [tw, tw1, tw2, tw3]

        for idx, e in enumerate(op_edges):

            if lext[idx] > 0:
                res = bmesh.ops.extrude_edge_only(bm, edges=[e])
                verts = filter_geom(res['geom'], BMVert)

                v = (calc_edge_median(e) - ref)
                v.normalize()

                flt_func = min if v.x > 0 else max
                mv1 = flt_func(list(e.verts), key=lambda v: v.co.x)
                mv2 = flt_func(verts, key=lambda v: v.co.x)

                bmesh.ops.translate(bm, verts=verts, vec=Vector((0, v.y, 0)) * lext[idx])
                bmesh.ops.translate(bm, verts=[mv1, mv2], vec=Vector((-v.x, 0, 0)) * wext[idx])

