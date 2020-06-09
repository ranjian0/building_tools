import bpy
import bmesh
from bpy.props import (
    IntProperty,
    EnumProperty,
    BoolProperty,
    FloatProperty,
    PointerProperty,
    CollectionProperty,
    FloatVectorProperty,
)

from ..utils import (
    clamp,
    bm_to_obj,
    bm_from_obj,
    get_edit_mesh,
    restricted_size,
    restricted_offset,
    set_material_for_active_facemap,
)


def get_count(self):
    """ Return count value with a default of 1
    """
    return self.get("count", 1)


def set_count(self, value):
    """ Set count value ensuring that element fit nicely in parent
    """
    # -- Make each element in array fit into the parent
    parent_width = self["wall_dimensions"][0]
    if self.size_offset.size.x > parent_width / value:
        self.size_offset.size.x = parent_width / value

    # -- keep horizontal offset within bounds of parent face
    element_width = parent_width / value
    item_width = self.size_offset.size.x
    max_offset = (element_width / 2) - (item_width / 2)
    self.size_offset.offset.x = clamp(
        self.size_offset.offset.x, -max_offset, max_offset
    )

    # -- set count
    self["count"] = value


def clamp_count(face_width, frame_width, prop):
    prop.count = clamp(prop.count, 1, int(face_width / frame_width) - 1)


CountProperty = IntProperty(
    name="Count",
    min=1,
    max=100,
    set=set_count,
    get=get_count,
    description="Number of elements",
)


class SizeOffsetProperty(bpy.types.PropertyGroup):
    """ Convinience PropertyGroup used for regular Quad Inset (see window and door)"""

    def get_size(self):
        if self["restricted"]:
            return self.get("size", restricted_size(
                self["parent_dimensions"], self.offset, (0.1, 0.1), self["default_size"]
            ))
        else:
            return self.get("size", self["default_size"])

    def set_size(self, value):
        if self["restricted"]:
            value = (clamp(value[0], 0.1, self["parent_dimensions"][0] - 0.0001), value[1])
            self["size"] = restricted_size(
                self["parent_dimensions"], self.offset, (0.1, 0.1), value
            )
        else:
            self["size"] = value

    size: FloatVectorProperty(
        name="Size",
        get=get_size,
        set=set_size,
        subtype="XYZ",
        size=2,
        description="Size of geometry",
    )

    def get_offset(self):
        return self.get("offset", self["default_offset"])

    def set_offset(self, value):
        self["offset"] = (
            restricted_offset(self["parent_dimensions"], self.size, value) if self["restricted"] else value
        )

    offset: FloatVectorProperty(
        name="Offset",
        get=get_offset,
        set=set_offset,
        subtype="TRANSLATION",
        size=2,
        description="How much to offset geometry",
    )

    show_props: BoolProperty(default=False)

    def init(self, parent_dimensions, default_size=(1.0, 1.0), default_offset=(0.0, 0.0), restricted=True):
        self["parent_dimensions"] = parent_dimensions
        self["default_size"] = default_size
        self["default_offset"] = default_offset
        self["restricted"] = restricted

    def draw(self, context, box):

        row = box.row(align=False)
        col = row.column(align=True)
        col.prop(self, "size")

        col = row.column(align=True)
        col.prop(self, "offset")


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
        description="How far arc is from top",
    )

    height: FloatProperty(
        name="Arc Height",
        get=get_height,
        set=set_height,
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


class BTOOLS_UL_fmaps(bpy.types.UIList):
    def draw_item(self, _context, layout, _data, item, icon, skip, _skip, _skip_):
        fmap = item
        if self.layout_type in {"DEFAULT", "COMPACT"}:
            layout.prop(fmap, "name", text="", emboss=False, icon="FACE_MAPS")
        elif self.layout_type == "GRID":
            layout.alignment = "CENTER"
            layout.label(text="", icon_value=icon)


class BTOOLS_OT_fmaps_clear(bpy.types.Operator):
    """Remove all empty face maps"""

    bl_idname = "btools.face_map_clear"
    bl_label = "Clear empty face maps"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        obj = context.object
        return obj and obj.type == "MESH"

    def execute(self, context):
        obj = context.object
        if obj.mode == "EDIT":
            me = get_edit_mesh()
            bm = bmesh.from_edit_mesh(me)
        else:
            bm = bm_from_obj(obj)

        face_map = bm.faces.layers.face_map.active
        used_indices = {f[face_map] for f in bm.faces}
        all_indices = {f.index for f in obj.face_maps}
        tag_remove_indices = all_indices - used_indices

        # -- remove face maps
        tag_remove_maps = [obj.face_maps[idx] for idx in tag_remove_indices]
        for fmap in tag_remove_maps:
            obj.face_maps.remove(fmap)

        # -- remove facemap materials:
        for idx in reversed(list(tag_remove_indices)):
            obj.facemap_materials.remove(idx)

        if obj.mode == "EDIT":
            bmesh.update_edit_mesh(me, True)
        else:
            bm_to_obj(bm, obj)
        return {"FINISHED"}


class TrackedProperty(bpy.types.PropertyGroup):
    """ Convinience property group to keep track of properties being
        shared between modules
    """

    slab_outset: FloatProperty()


def update_facemap_material(self, context):
    """ Assign the updated material to all faces belonging to active facemap
    """
    set_material_for_active_facemap(self.material, context)
    return None


class FaceMapMaterial(bpy.types.PropertyGroup):
    """ Tracks materials for each facemap created for an object
    """

    material: PointerProperty(type=bpy.types.Material, update=update_facemap_material)

    auto_map: BoolProperty(
        name="Auto UV Mapping",
        default=True,
        description="Automatically UV Map faces belonging to active facemap.")

    mapping_methods = [
        ("UNWRAP", "Unwrap", "", 0),
        ("CUBE_PROJECTION", "Cube_Projection", "", 1),
    ]

    uv_mapping_method: EnumProperty(
        name="UV Mapping Method",
        items=mapping_methods,
        default="CUBE_PROJECTION",
        description="How to perform UV Mapping"
    )


classes = (
    ArchProperty,
    FaceMapMaterial,
    TrackedProperty,
    BTOOLS_UL_fmaps,
    SizeOffsetProperty,
    BTOOLS_OT_fmaps_clear,
)


def register_generic():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Object.tracked_properties = PointerProperty(type=TrackedProperty)
    bpy.types.Object.facemap_materials = CollectionProperty(type=FaceMapMaterial)


def unregister_generic():
    for cls in classes:
        bpy.utils.unregister_class(cls)

    del bpy.types.Object.facemap_materials
    del bpy.types.Object.tracked_properties
