import bpy 
from bpy.props import (
    BoolProperty,
    FloatProperty,
    FloatVectorProperty,
)

from ..utils import (
    clamp,
    restricted_size,
    restricted_offset,
)

from mathutils import Vector

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


class SizeOffsetGetSet:
    """ Provide getset redirection in classes that use SizeOffsetProperty
    i.e allow for Parent.width instead of Parent.size_offset.size.x
    """

    @property
    def width(self):
        return self.size_offset.size.x 

    @width.setter 
    def width(self, val):
        self.size_offset.size.x = val

    @property 
    def height(self):
        return self.size_offset.size.y 

    @height.setter
    def height(self, val):
        self.size_offset.size.y = val 

    @property 
    def size(self):
        return self.size_offset.size 

    @size.setter 
    def size(self, val):
        self.size_offset.size = val

    @property 
    def offsetx(self):
        return self.size_offset.offset.x
    
    @offsetx.setter 
    def offsetx(self, val):
        self.size_offset.offset.x = val 

    @property 
    def offsety(self):
        return self.size_offset.offset.y
    
    @offsety.setter 
    def offsety(self, val):
        self.size_offset.offset.y = val 

    @property 
    def offset(self):
        return self.size_offset.offset
    
    @offset.setter 
    def offset(self, val):
        self.size_offset.offset = val 
