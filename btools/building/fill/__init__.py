import bpy

from .fill_ops import BTOOLS_OT_add_fill
from .fill_props import FillBars, FillGlassPanes, FillLouver, FillPanel, FillProperty
from .fill_types import fill_face as fill_face

classes = (
    FillBars,
    FillPanel,
    FillLouver,
    FillGlassPanes,
    FillProperty,
    BTOOLS_OT_add_fill,
)


register_fill, unregister_fill = bpy.utils.register_classes_factory(classes)
