import bpy
import bmesh
from math import pi, sin
from pprint import pprint
from mathutils import Matrix, Vector
from bmesh.types import BMVert, BMEdge, BMFace
from .utils import (
        split,
        filter_geom,
        filter_horizontal_edges,
        filter_vertical_edges,
        calc_face_dimensions,
        calc_edge_median,
        kwargs_from_props,
        square_face,
        select,
        bm_from_obj,
        bm_to_obj,
        index_from_facedata
    )

"""
TODO:
    - Remove split edge in the arched window
"""

class Window:

    @classmethod
    def build(cls, context, facedata_list=[], update=False, id=0):
        """ Create window geometry from selected faces """

        obj = context.object
        prop_id = id if update else obj.property_list[obj.property_index].id
        props = obj.building.windows[prop_id]

        cls.facedata_list = facedata_list
        cls.update = update
        if props.type == 'BASIC':
            cls.generate_type_basic(**kwargs_from_props(props))
        else:
            cls.generate_type_arched(**kwargs_from_props(props))

    @classmethod
    def generate_type_basic(cls, **kwargs):
        """ Generic window with inset panes """

        # Get active mesh
        obj = bpy.context.object

        bm = bm_from_obj(obj)

        if cls.update:
            # Find face with corresponding facedata
            indices = [index_from_facedata(obj, bm, fd) for fd in cls.facedata_list]

            # Find faces with given indices
            faces = [f for f in bm.faces if f.index in indices]
        else:
            faces = [f for f in bm.faces if f.index in cls.facedata_list]

        for face in faces:

            # -- add a split
            face = cls.make_window_split(bm, face, **kwargs)

            # -- check that split was successful
            if not face: 
                return

            # -- create window frame
            face = cls.make_window_frame(bm, face, **kwargs)

            # -- add some window panes/bars
            fill = kwargs.get('fill')
            if fill == 'BAR':
                cls.make_window_bars(bm, face, **kwargs)
            else:
                cls.make_window_panes(bm, face, **kwargs)

        # bmesh.update_edit_mesh(me, True)
        bm_to_obj(bm, obj)

    @classmethod
    def generate_type_arched(cls, **kwargs):
        """ Generic window with an arch top and panes """

        # Get active mesh
        me = bpy.context.edit_object.data
        bm = bmesh.from_edit_mesh(me)

        # Find selected faces
        faces = [f for f in bm.faces if f.select]

        for face in faces:
            face.select = False

            # -- add a split
            face = cls.make_window_split(bm, face, **kwargs)

            # -- check that split was successful
            if not face: 
                return

            # subdivide the face horizontally
            e = filter_vertical_edges(face.edges, face.normal)
            res = bmesh.ops.subdivide_edges(bm, edges=e, cuts=1)
            nedge = filter_geom(res['geom_inner'], BMEdge)[-1]

            upper_face = face 
            lower_face = list(set(nedge.link_faces).difference([upper_face]))[-1]

            # -- make upperface arch
            cls.make_window_arch(bm, upper_face, **kwargs)

            # create window frame
            upper_face = cls.make_window_frame(bm, upper_face, **kwargs)

            # Arch detail
            cls.make_window_arch_detail(bm, upper_face, **kwargs)

            # -- make lowerface panes/bars
            lower_face = cls.make_window_frame(bm, lower_face, **kwargs)

            fill = kwargs.get('fill')
            if fill == 'BAR':
                cls.make_window_bars(bm, lower_face, **kwargs)
            else:
                cls.make_window_panes(bm, lower_face, **kwargs)

        bmesh.update_edit_mesh(me, True)
            
    @classmethod
    def make_window_split(cls, bm, face, amount=Vector((2, 2)), off=Vector((0,0,0)), has_split=True, **kwargs):
        """ Basically scales down the face given based on parameters """
        if has_split:
            return split(bm, face, amount.y, amount.x, off.x, off.y, off.z)
        return face

    @classmethod
    def make_window_frame(cls, bm, face, ft=0.05, fd=0.05, **kwargs):
        """ Inset and extrude to create a frame """

        # if there any double vertices we're in trouble
        bmesh.ops.remove_doubles(bm, verts=list(bm.verts))

        # Make frame inset - frame thickness
        if ft > 0:
            bmesh.ops.inset_individual(bm, faces=[face], thickness=ft)

        # Make frame extrude - frame depth
        # --fucking normals
        bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
        if fd > 0:
            ret = bmesh.ops.extrude_discrete_faces(bm, faces=[face])
            f = ret['faces'][0]
            bmesh.ops.translate(bm, verts=f.verts, vec=-f.normal * fd)
            return f
        return face

    @classmethod
    def make_window_panes(cls, bm, face, px=1, py=1, pt=.05, pd=0.05, **kwargs):
        """ Create some window panes """

        n = face.normal
        v_edges = filter_vertical_edges(face.edges, n)
        h_edges = filter_horizontal_edges(face.edges, n)

        # -- if panes_x == 0, skip
        if px:
            res1 = bmesh.ops.subdivide_edges(bm, edges=v_edges, cuts=px)

        edgs = filter_geom(res1['geom_inner'], BMEdge) if px else []
        if py:
            res2 = bmesh.ops.subdivide_edges(bm, edges=h_edges + edgs, cuts=py)

        # panes
        # -- if we're here successfully, about 3 things may have happened
        do_panes = True
        if py:
            e = filter_geom(res2['geom_inner'], BMEdge)
        else:
            if px:
                e = edgs
            else:
                do_panes = False
        if do_panes:
            pane_faces = list({f for ed in e for f in ed.link_faces})
            panes = bmesh.ops.inset_individual(bm, faces=pane_faces, thickness=pt)

            for f in pane_faces:
                bmesh.ops.translate(bm, verts=f.verts, vec=-f.normal * pd)

        pass

    @classmethod
    def make_window_bars(cls, bm, face, fd=.1, px=1, py=1, pt=.05, pd=0.05, **kwargs):
        """ Create window bars """

        # Calculate center, width and height of face
        width, height = calc_face_dimensions(face)
        fc = face.calc_center_median()

        # Create Inner Frames
        # -- horizontal
        offset = height / (px + 1)
        for i in range(px):
            # Duplicate
            ret = bmesh.ops.duplicate(bm, geom=[face])
            square_face(bm, filter_geom(ret['geom'], BMFace)[-1])
            verts = filter_geom(ret['geom'], BMVert)

            # Scale and translate
            bmesh.ops.scale(bm, verts=verts, vec=(1, 1, pt), space=Matrix.Translation(-fc))
            bmesh.ops.translate(bm, verts=verts,
                                vec=Vector((face.normal * fd / 2)) + Vector((0, 0, -height / 2 + (i + 1) * offset)))

            # Extrude
            ext = bmesh.ops.extrude_edge_only(bm,
                                              edges=filter_horizontal_edges(filter_geom(ret['geom'], BMEdge), face.normal))
            bmesh.ops.translate(bm, verts=filter_geom(ext['geom'], BMVert), vec=-face.normal * fd / 2)

        # -- vertical
        eps = 0.015
        offset = width / (py + 1)
        for i in range(py):
            # Duplicate
            ret = bmesh.ops.duplicate(bm, geom=[face])
            verts = filter_geom(ret['geom'], BMVert)

            # Scale and Translate
            bmesh.ops.scale(bm, verts=verts, vec=(pt, pt, 1), space=Matrix.Translation(-fc))
            perp = face.normal.cross(Vector((0, 0, 1)))
            bmesh.ops.translate(bm, verts=verts,
                                vec=Vector((face.normal * ((fd / 2) - eps))) + perp * (-width / 2 + ((i + 1) * offset)))

            # Extrude
            ext_edges = []

            # filter vertical edges
            # -- This part is redundant for good reasons, JUST DON'T!!

            if face.normal.x and face.normal.y:
                for e in filter_geom(ret['geom'], BMEdge):
                    s = set([round(v.co.x, 4) for v in e.verts])
                    if len(s) == 1:
                        ext_edges.append(e)
            elif face.normal.x and not face.normal.y:
                for e in filter_geom(ret['geom'], BMEdge):
                    s = set([round(v.co.y, 4) for v in e.verts])
                    if len(s) == 1:
                        ext_edges.append(e)
            elif face.normal.y and not face.normal.x:
                for e in filter_geom(ret['geom'], BMEdge):
                    s = set([round(v.co.x, 4) for v in e.verts])
                    if len(s) == 1:
                        ext_edges.append(e)
            else:
                raise NotImplementedError

            ext = bmesh.ops.extrude_edge_only(bm, edges=ext_edges)
            bmesh.ops.translate(bm, verts=filter_geom(ext['geom'], BMVert), vec=-face.normal * ((fd / 2) - eps))

    @classmethod
    def make_window_arch(cls, bm, face, ares=3, aoff=.5, aheight=.4, **kwargs):
        """ Arc the top edge of a face """

        #bmesh.ops.inset_individual(bm, faces=[face], thickness= aheight / ares)
        # Get top edge
        top = sorted([e for e in face.edges], key=lambda ed: calc_edge_median(ed).z)[-1]

        # Subdivide
        ret = bmesh.ops.subdivide_edges(bm, edges=[top], cuts=ares)

        # Sort Verts
        verts = list({v for e in filter_geom(ret['geom_split'], BMEdge) for v in e.verts})
        if face.normal.y:
            verts.sort(key=lambda v: v.co.x)
        else:
            verts.sort(key=lambda v: v.co.y)

        # Offset verts along sin curve
        angle = pi / (len(verts)-1)
        for idx, v in enumerate(verts):
            off = sin(angle*idx) * aheight
            v.co.z -= aoff
            v.co.z += off 

    @classmethod
    def make_window_arch_detail(cls, bm, face, adetail=True, dthick=.03, ddepth=.01, **kwargs):
        """ Create detail in the arched face """
        if not adetail:
            return

        fn = face.normal
        # Poke face
        res = bmesh.ops.poke(bm, faces=[face])

        # inset and extrude
        if dthick > 0:
            ret = bmesh.ops.inset_individual(bm, faces=res['faces'], thickness=dthick)
            bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    
            ret = bmesh.ops.extrude_discrete_faces(bm, faces=res['faces'])
            verts = [v for f in ret['faces'] for v in f.verts]
            bmesh.ops.translate(bm, verts=verts, vec=-fn * ddepth)