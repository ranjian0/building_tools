import bpy
from bpy.props import (
        IntProperty,
        BoolProperty,
        EnumProperty,
        FloatProperty,
        StringProperty,
        PointerProperty,
        FloatVectorProperty
    )
from ..utils import get_material_wrapper
from bpy_extras.image_utils import load_image


class SizeOffsetProperty(bpy.types.PropertyGroup):
    """ Convinience PropertyGroup used for regular Quad Inset (see window and door)"""
    size : FloatVectorProperty(
        name="Size", min=.01, max=1.0, subtype='XYZ', size=2, default=(0.7, 0.7),
        description="Size of geometry")

    off  : FloatVectorProperty(
        name="Offset", min=-1000.0, max=1000.0, subtype='TRANSLATION', size=3, default=(0.0, 0.0, 0.0),
        description="How much to offset geometry")

    collapsed : BoolProperty(default=True)

    def draw(self, context, layout):
        box = layout.box()
        box.prop(self, 'collapsed', text="Size & Offset", toggle=True)

        if not self.collapsed:
            row = box.row(align=False)

            col = row.column(align=True)
            col.prop(self, 'size', slider=True)

            col = row.column(align=True)
            col.prop(self, 'off')

def update_material(self, context):
    obj = context.object
    group = self

    principled = get_material_wrapper(group.material)
    principled.base_color = group.base_color
    if group.base_color_texture:
        principled.base_color_texture.image = load_image(group.base_color_texture)

    principled.specular = group.specular
    if group.specular_texture:
        principled.specular_texture.image = load_image(group.specular_texture)

    principled.normalmap_strength = group.normalmap_strength
    if group.normalmap_texture:
        principled.normalmap_texture.image = load_image(group.normalmap_texture)

    principled.metallic = group.metallic
    if group.metallic_texture:
        principled.metallic_texture.image = load_image(group.metallic_texture)

def change_material(self, context):
    obj = context.object
    group = self

    principled = get_material_wrapper(group.material)
    group.base_color = principled.base_color
    if principled.base_color_texture.image:
        group.base_color_texture = principled.base_color_texture.image.filepath

    group.specular = principled.specular
    if principled.specular_texture.image:
        group.specular_texture = principled.specular_texture.image.filepath

    group.normalmap_strength = principled.normalmap_strength
    if principled.normalmap_texture.image:
        group.normalmap_texture = principled.normalmap_texture.image.filepath

    group.metallic = principled.metallic
    if principled.metallic_texture.image:
        group.metallic_texture = principled.metallic_texture.image.filepath

class MaterialGroup(bpy.types.PropertyGroup):
    """ PropertyGroup to hold Material Data"""
    name     : StringProperty()
    material : PointerProperty(type=bpy.types.Material, update=change_material)

    mat_items = [
        ("BASE", "Base", "", 0),
        ("SPECULAR", "Specular", "", 1),
        ("NORMAL", "Normal", "", 2),
        ("METALLIC", "Metallic", "", 3)
    ]
    mat_options : EnumProperty(items=mat_items, default="BASE")

    base_color : FloatVectorProperty(subtype='COLOR', default=(0.8, 0.8, 0.8), update=update_material)
    base_color_texture : StringProperty(subtype='FILE_PATH', update=update_material)

    specular : FloatProperty(default=0.5, min=0.0, max=1.0, update=update_material)
    specular_texture : StringProperty(subtype='FILE_PATH', update=update_material)

    normalmap_strength : FloatProperty(default=0.0, min=0.0, max=1.0, update=update_material)
    normalmap_texture : StringProperty(subtype='FILE_PATH', update=update_material)

    metallic : FloatProperty(default=0.0, min=0.0, max=1.0, update=update_material)
    metallic_texture : StringProperty(subtype='FILE_PATH', update=update_material)


classes = (
    MaterialGroup,
    SizeOffsetProperty,
)

def register_generic():
    for cls in classes:
        bpy.utils.register_class(cls)

    # bpy.types.Object.mat_groups = bpy.props.CollectionProperty(type=MaterialGroup)
    # bpy.types.Object.mat_group_index = bpy.props.IntProperty()

def unregister_generic():
    for cls in classes:
        bpy.utils.unregister_class(cls)

    # del bpy.types.Object.mat_groups
    # del bpy.types.Object.mat_group_index
