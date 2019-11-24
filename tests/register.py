import bpy
from .generic import BTOOLS_PT_test_tools
from .test_door import BTOOLS_OT_test_door
from .test_floors import BTOOLS_OT_test_floors
from .test_window import BTOOLS_OT_test_window
from .test_floorplan import BTOOLS_OT_test_floorplan

classes = (
    BTOOLS_PT_test_tools,

    BTOOLS_OT_test_door,
    BTOOLS_OT_test_floors,
    BTOOLS_OT_test_window,
    BTOOLS_OT_test_floorplan,
)


def register_tests():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister_tests():
    for cls in classes:
        bpy.utils.unregister_class(cls)
