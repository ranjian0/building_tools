import bpy

from .batch_ops import BTOOLS_OT_batch_generate
from .batch_props import BatchProperty

classes = (BatchProperty, BTOOLS_OT_batch_generate)

register_batch, unregister_batch = bpy.utils.register_classes_factory(classes)
