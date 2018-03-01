import bmesh
from bmesh.types import BMVert, BMEdge, BMFace
from .utils import (
    kwargs_from_props,
    get_edit_mesh,
    filter_geom,
)


class Floor:

    @classmethod
    def build(cls, context):
        """ Create the floorplan based on a floorplan object """

        # -- ensure that edit mesh is a valid floorplan - (planar)
        if not cls.check_planar():
            return

        # -- now we can create floors
        props = context.object.building.floors
        cls.make_floors(**kwargs_from_props(props))

    @classmethod
    def check_planar(cls):
        """ Check to see in active mesh is planar """

        # -- get current edit mesh
        me = get_edit_mesh()

        # -- check that all verts are on same z coordinate
        if len(set([v.co.z for v in me.vertices])) == 1:
            return True
        return False

    @classmethod
    def make_floors(cls, floor_count=1, floor_height=2, slab_thickness=.1, slab_outset=.1, **kwargs):
        """ Create a set of extrusions given a base plane (forms building block) """

        # -- get current edit mesh
        me = get_edit_mesh()
        bm = bmesh.from_edit_mesh(me)

        # -- find boundary edges
        edges = [e for e in bm.edges if e.is_boundary]

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
            verts = filter_geom(floor_ext['geom'], BMVert)
            edges = filter_geom(floor_ext['geom'], BMEdge)
            bmesh.ops.translate(bm, vec=(0, 0, floor_height), verts=verts)

            # Offset Slab
            bmesh.ops.inset_region(bm, faces=slab_faces, depth=-slab_outset)

        # -- fill top face
        bmesh.ops.contextual_create(bm, geom=edges)

        # -- update normals and mesh
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bmesh.update_edit_mesh(me, True)
