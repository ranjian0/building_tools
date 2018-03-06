import bpy
import bmesh
from bmesh.types import BMEdge, BMVert
from mathutils import Vector
from .utils import (
        split,
        filter_geom,
        filter_vertical_edges,
        filter_horizontal_edges,
        kwargs_from_props,
        index_from_facedata,
        bm_from_obj,
        bm_to_obj
    )


class Door:

    @classmethod
    def build(cls, context, facedata_list=[], update=False, id=0):
        """ Build door geomerty from selected faces """

        obj = context.object
        prop_id = id if update else obj.property_list[obj.property_index].id
        props = obj.building.doors[prop_id]

        cls.facedata_list = facedata_list
        cls.update = update
        cls.generate_door(**kwargs_from_props(props))

    @classmethod
    def generate_door(cls, **kwargs):

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
            face = cls.make_door_split(bm, face, **kwargs)

            if not face:
                return

            # -- create door frame
            face = cls.make_door_frame(bm, face, **kwargs)

            # -- chack double door
            nfaces = cls.make_door_double(bm, face, **kwargs)


            for face in nfaces:
                # create door outline
                face = cls.make_door_outline(bm, face, **kwargs)

                face = cls.make_door_panes(bm, face, **kwargs)

                cls.make_door_grooves(bm, face, **kwargs)

        bm_to_obj(bm, obj)

    @classmethod
    def make_door_split(cls, bm, face, amount=Vector((2, 2)), off=Vector((0,0,0)), has_split=True, **kwargs):
        if has_split:
            return split(bm, face, amount.y, amount.x, off.x, off.y, off.z)
        return face

    @classmethod
    def make_door_frame(cls, bm, face, oft=0.05, ofd=0.05, **kwargs):

        # if there any double vertices we're in trouble
        bmesh.ops.remove_doubles(bm, verts=list(bm.verts))

        # Make frame inset - frame thickness
        if oft > 0:
            res = bmesh.ops.inset_individual(bm, faces=[face], thickness=oft)

        # Make frame extrude - frame depth
        bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
        if ofd > 0:
            ret = bmesh.ops.extrude_discrete_faces(bm, faces=[face])
            f = ret['faces'][0]
            bmesh.ops.translate(bm, verts=f.verts, vec=-f.normal * ofd)

            return f
        return face

    @classmethod
    def make_door_double(cls, bm, face, hdd=False, **kwargs):
        if hdd:
            edgs = filter_horizontal_edges(face.edges, face.normal)
            ret = bmesh.ops.subdivide_edges(bm, edges=edgs, cuts=1)
            new_faces = list(filter_geom(ret['geom_inner'], BMEdge)[-1].link_faces)

            return new_faces
        return [face]

    @classmethod
    def make_door_outline(cls, bm, face, ift=0.0, ifd=0.0, **kwargs):
        if ift > 0:
            bmesh.ops.inset_individual(bm, faces=[face], thickness=ift)
            if ifd > 0:
                ret = bmesh.ops.extrude_discrete_faces(bm, faces=[face])
                face = ret['faces'][0]
                bmesh.ops.translate(bm, verts=face.verts, vec=-face.normal * ifd)
                return face
        return face

    @classmethod
    def make_door_panes(cls, bm, face, panned=False, px=2, py=2, pt=.01, pd=.01, offset=0.5, width=.7, **kwargs):
        if not panned:
            return face

        n = face.normal
        v_edges = filter_vertical_edges(face.edges, n)
        res = bmesh.ops.subdivide_edges(bm, edges=v_edges, cuts=2)
        edges = filter_geom(res['geom_inner'], BMEdge)

        ret_face = min({f for e in edges for f in e.link_faces}, key=lambda f: f.calc_center_median().z)

        bmesh.ops.scale(bm, verts=list({v for e in edges for v in e.verts}), vec=(1, 1, width))
        bmesh.ops.translate(bm, verts=list({v for e in edges for v in e.verts}), vec=(0, 0, offset))

        # get pane face
        pane_face = list(set(list(edges)[0].link_faces).intersection(set(list(edges)[1].link_faces)))[-1]
        bmesh.ops.inset_individual(bm, faces=[pane_face], thickness=0.01)

        # cut panes
        vedgs = filter_vertical_edges(pane_face.edges, n)
        hedgs = list((set(pane_face.edges).difference(vedgs)))

        res1 = bmesh.ops.subdivide_edges(bm, edges=vedgs, cuts=px)
        edgs = filter_geom(res1['geom_inner'], BMEdge)
        res2 = bmesh.ops.subdivide_edges(bm, edges=hedgs + edgs, cuts=py)

        # panels
        e = filter_geom(res2['geom_inner'], BMEdge)
        pane_faces = list({f for ed in e for f in ed.link_faces})
        panes = bmesh.ops.inset_individual(bm, faces=pane_faces, thickness=pt)

        for f in pane_faces:
            bmesh.ops.translate(bm, verts=f.verts, vec=-f.normal * pd)

        return ret_face

    @classmethod
    def make_door_grooves(cls, bm, face, grov=False, gx=3, gy=1, gt=.1, gd=.01, gw=1, goff=0, **kwargs):
        if not grov:
            return

        # Create main groove to hold child grooves
        bmesh.ops.inset_individual(bm, faces=[face], thickness=gt)
        bmesh.ops.scale(bm, verts=list({v for e in face.edges for v in e.verts}), vec=(1, 1, gw))
        bmesh.ops.translate(bm, verts=list({v for e in face.edges for v in e.verts}), vec=(0, 0, goff))

        # Calculate edges to be subdivided
        n = face.normal
        vedgs = filter_vertical_edges(face.edges, n)
        hedgs = list((set(face.edges).difference(vedgs)))

        # Subdivide the edges
        res1 = bmesh.ops.subdivide_edges(bm, edges=vedgs, cuts=gx)
        edgs = filter_geom(res1['geom_inner'], BMEdge)
        res2 = bmesh.ops.subdivide_edges(bm, edges=hedgs + edgs, cuts=gy)

        # Get all groove faces
        vts = filter_geom(res2['geom_inner'], BMVert)
        faces = list(filter(lambda f: len(f.verts) == 4, {f for v in vts for f in v.link_faces if f.normal == n}))

        # Make groove
        bmesh.ops.inset_individual(bm, faces=faces, thickness=gt / 2)
        bmesh.ops.inset_individual(bm, faces=faces, thickness=gt / 2)

        v = list({v for f in faces for v in f.verts})
        bmesh.ops.translate(bm, verts=v, vec=n * gd)

        # Clean geometry
        vts2 = [v for e in filter_geom(res1['geom_split'], BMEdge) for v in e.verts]
        vts2.sort(key=lambda v: v.co.z)
        vts2 = vts2[2:len(vts2) - 2]

        bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=0.0)
        bmesh.ops.dissolve_verts(bm, verts=list(set(vts + vts2)))
        bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
