import bpy
import bmesh
from bmesh.types import BMVert, BMEdge, BMFace
from .utils import (
    kwargs_from_props,
    bm_from_obj,
    filter_geom,
    bm_to_obj,
    material_set_faces,
    floor_mat_slab,
    floor_mat_wall,
    select
)


class Floor:

    @classmethod
    def build(cls, context, update=False):
        """ Build floorplan geomerty from properties """

        # -- ensure that the mesh is a valid floorplan - (planar)
        if not cls.check_planar():
            return

        # -- create geometry
        setattr(cls, "update", update)
        props = context.object.building.floors
        cls.make_floors(**kwargs_from_props(props))

    @classmethod
    def check_planar(cls):
        """ Check to see in active mesh is planar """

        # -- get current object bmesh
        obj = bpy.context.object
        bm = bm_from_obj(obj)

        # -- check that all verts are on same z coordinate
        if len(set([v.co.z for v in bm.verts])) == 1:
            bm_to_obj(bm, obj)
            return True
        bm_to_obj(bm, obj)
        return False

    @classmethod
    def make_floors(cls, floor_count=1, floor_height=2, slab_thickness=.1, slab_outset=.1, **kwargs):
        """ Create a set of extrusions given a base plane (forms building block) """
        obj = bpy.context.object

        # -- make/get materials
        slab_mat = kwargs.get("mat_slab")
        wall_mat = kwargs.get("mat_wall")
        if not slab_mat
            slab_mat = floor_mat_slab(obj)
            obj.building.floors.mat_slab = slab_mat
        if not wall_mat:
            wall_mat = floor_mat_wall(obj)
            obj.building.floors.mat_wall = wall_mat

        mslab_faces, mfloor_faces = [], []

        # -- get active object bmesh
        bm = bm_from_obj(obj)

        # -- find boundary edges
        edges = [e for e in bm.edges if e.is_boundary]

        # -- floorplan faces are alsb material
        mslab_faces.extend([f for f in bm.faces])

        # -- extrude floor and slabs
        for i in range(floor_count):
            # Extrude slab
            slab_ext = bmesh.ops.extrude_edge_only(bm, edges=edges)
            slab_faces = filter_geom(slab_ext['geom'], BMFace)
            verts = filter_geom(slab_ext['geom'], BMVert)
            edges = filter_geom(slab_ext['geom'], BMEdge)
            bmesh.ops.translate(bm, vec=(0, 0, slab_thickness), verts=verts)

            # Extrude floor
            floor_ext = bmesh.ops.extrude_edge_only(bm, edges=edges)
            floor_faces = filter_geom(floor_ext['geom'], BMFace)
            verts = filter_geom(floor_ext['geom'], BMVert)
            edges = filter_geom(floor_ext['geom'], BMEdge)
            bmesh.ops.translate(bm, vec=(0, 0, floor_height), verts=verts)

            # Offset Slab
            ret = bmesh.ops.inset_region(bm, faces=slab_faces, depth=-slab_outset)

            # Material faces
            mslab_faces.extend(slab_faces+ret['faces'])
            mfloor_faces.extend(floor_faces)

        # -- fill top face
        ret = bmesh.ops.contextual_create(bm, geom=edges)
        mslab_faces.extend(ret['faces'])

        # Set materials
        unique = lambda lst : list(set(lst))
        material_set_faces(obj, slab_mat, unique(mslab_faces))
        material_set_faces(obj, wall_mat, unique(mfloor_faces))

        # -- update normals and mesh
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm_to_obj(bm, obj)