import bpy
from bpy.props import (
    IntProperty,
    EnumProperty,
    BoolProperty,
    FloatProperty,
    FloatVectorProperty,
)
from mathutils import Vector

from ..utils import (
    clamp,
    restricted_size,
    restricted_offset,
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

    def clamp_size(self):
        if self["restricted"]:
            value = (clamp(self.size[0], 0.1, self["parent_dimensions"][0] - 0.0001), self.size[1])
            self.size = restricted_size(
                self["parent_dimensions"], self.offset, (0.1, 0.1), value
            )

    def set_size_width(self, value):
        self.size[0] = value
        self.clamp_size()

    def set_size_height(self, value):
        self.size[1] = value
        self.clamp_size()

    def get_size(self):
        if self["restricted"]:
            size = self.get("size", restricted_size(
                self["parent_dimensions"], self.offset, (0.1, 0.1), self["default_size"]
            ))
        else:
            size = self.get("size", self["default_size"])
        self.size = size
        return size

    def get_size_width(self):
        return self.get_size()[0]

    def get_size_height(self):
        return self.get_size()[1]

    # Used internally, hidden
    size: FloatVectorProperty(
        name="Size",
        subtype="XYZ",
        size=2,
        unit="LENGTH",
        description="Size of geometry",
    )

    size_width: FloatProperty(
        name="Width",
        set=set_size_width,
        get=get_size_width,
        unit="LENGTH",
        description="Width of geometry",
    )

    size_height: FloatProperty(
        name="Height",
        set=set_size_height,
        get=get_size_height,
        unit="LENGTH",
        description="Height of geometry",
    )

    def clamp_offset(self):
        self.offset = (
            restricted_offset(self["parent_dimensions"], self.size, self.offset) if self["restricted"] else self.offset
        )

    def set_offset_horizontal(self, value):
        self.offset[0] = value
        self.clamp_offset()

    def set_offset_vertical(self, value):
        self.offset[1] = value
        self.clamp_offset()

    def get_offset(self):
        offset = self.get("offset", self["default_offset"])
        self.offset = offset
        return offset

    def get_offset_horizontal(self):
        return self.get_offset()[0]

    def get_offset_vertical(self):
        return self.get_offset()[1]

    # Used internally, hidden
    offset: FloatVectorProperty(
        name="Offset",
        subtype="TRANSLATION",
        size=2,
        unit="LENGTH",
        description="How much to offset geometry",
    )

    offset_horizontal: FloatProperty(
        name="Horizontal",
        set=set_offset_horizontal,
        get=get_offset_horizontal,
        unit="LENGTH",
        description="How much to offset geometry horizontally",
    )

    offset_vertical: FloatProperty(
        name="Vertical",
        set=set_offset_vertical,
        get=get_offset_vertical,
        unit="LENGTH",
        description="How much to offset geometry vertically",
    )

    show_props: BoolProperty(default=False)

    def init(self, parent_dimensions, default_size=(1.0, 1.0), default_offset=(0.0, 0.0), restricted=True):
        self["parent_dimensions"] = parent_dimensions
        self["default_size"] = default_size
        self["default_offset"] = default_offset
        self["restricted"] = restricted

        if self.size == Vector((0, 0)):
            self.size = default_size
            self.offset = default_offset

    def draw(self, context, box):

        row = box.row(align=False)
        col = row.column(align=True)
        col.label(text="Size:")
        col.prop(self, "size_width")
        col.prop(self, "size_height")

        col = row.column(align=True)
        col.label(text="Offset:")
        col.prop(self, "offset_horizontal")
        col.prop(self, "offset_vertical")


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


classes = (
    ArchProperty,
    SizeOffsetProperty,
)


def register_generic():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister_generic():
    for cls in classes:
        bpy.utils.unregister_class(cls)
