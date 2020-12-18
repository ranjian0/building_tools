import bpy
import bmesh
from bmesh.types import BMEdge
from bpy.props import (
    IntProperty,
    EnumProperty,
    FloatProperty,
)

from ..utils import (
    FaceMap,
    arc_edge,
    sort_verts,
    filter_geom,
    map_new_faces,
    get_bottom_faces,
    extrude_face_region,
    add_facemap_for_groups,
)


class ArchProperty(bpy.types.PropertyGroup):
    """ Convinience PropertyGroup to create arched features """

    def get_height(self):
        return self.get("height", min(self["parent_height"], self["default_height"]))

    def set_height(self, value):
        self["height"] = clamp(value, 0.1, self["parent_height"] - 0.0001)

    resolution: IntProperty(
        name="Arc Resolution",
        min=1,
        max=128,
        default=6,
        description="Number of segements for the arc",
    )

    depth: FloatProperty(
        name="Arc Depth",
        min=0.01,
        max=1.0,
        default=0.05,
        unit="LENGTH",
        description="How far arc is from top",
    )

    height: FloatProperty(
        name="Arc Height",
        get=get_height,
        set=set_height,
        unit="LENGTH",
        description="Radius of the arc",
    )

    func_items = [("SINE", "Sine", "", 0), ("SPHERE", "Sphere", "", 1)]
    function: EnumProperty(
        name="Offset Function",
        items=func_items,
        default="SPHERE",
        description="Type of offset for arch",
    )

    def init(self, parent_height):
        self["parent_height"] = parent_height
        self["default_height"] = 0.4

    def draw(self, context, box):

        col = box.column(align=True)
        row = col.row(align=True)
        row.prop(self, "function", expand=True)
        col.prop(self, "resolution")
        col.prop(self, "depth")
        col.prop(self, "height")


def fill_arch(bm, face, prop):
    """ Fill arch
    """
    if prop.fill_type == "GLASS_PANES":
        add_facemap_for_groups(FaceMap.DOOR_PANES)
        pane_arch_face(bm, face, prop.glass_fill)


def create_arch(bm, top_edges, frame_faces, arch_prop, frame_thickness, xyz):
    """ Create arch using top edges of extreme frames
    """
    verts = sort_verts([v for e in top_edges for v in e.verts], xyz[0])
    arc_edges = [
        bmesh.ops.connect_verts(bm, verts=[verts[0], verts[-1]])["edges"].pop(),
        bmesh.ops.connect_verts(bm, verts=[verts[1], verts[-2]])["edges"].pop(),
    ]

    resolution, height, function = arch_prop.resolution, arch_prop.height, arch_prop.function
    upper_arc = filter_geom(
        arc_edge(bm, arc_edges[0], resolution, height, xyz, function)["geom_split"], BMEdge)
    lower_arc = filter_geom(
        arc_edge(bm, arc_edges[1], resolution, height-frame_thickness, xyz, function)["geom_split"], BMEdge)
    arc_edges = [*upper_arc, *lower_arc]

    arc_face = min(upper_arc[arch_prop.resolution//2].link_faces, key=lambda f: f.calc_center_median().z)
    bmesh.ops.delete(bm, geom=[arc_face], context="FACES")

    arch_frame_faces = bmesh.ops.bridge_loops(bm, edges=arc_edges)["faces"]
    arch_face = min(lower_arc[arch_prop.resolution//2].link_faces, key=lambda f: f.calc_center_median().z)

    if len(verts) == 4: # corner case
        verts = sort_verts([v for e in top_edges for v in e.verts], xyz[0])
        new_edge = bmesh.ops.connect_verts(bm, verts=[verts[1], verts[-2]])['edges'].pop()
        new_face = get_bottom_faces(new_edge.link_faces).pop()
        arch_frame_faces.append(new_face)

    return arch_face, arch_frame_faces


@map_new_faces(FaceMap.DOOR_PANES)
def pane_arch_face(bm, face, prop):
    bmesh.ops.inset_individual(
        bm, faces=[face], thickness=prop.pane_margin * 0.75, use_even_offset=True
    )
    bmesh.ops.translate(bm, verts=face.verts, vec=-face.normal * prop.pane_depth)


def add_arch_depth(bm, arch_face, depth, normal):
    """ Add depth to arch face
    """
    if depth > 0.0:
        arch_faces, frame_faces = extrude_face_region(bm, [arch_face], -depth, normal)
        return arch_faces[0], frame_faces
    else:
        return arch_face, []
