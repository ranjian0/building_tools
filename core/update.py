import bpy
from .floor import Floor
from .floorplan import Floorplan
# from .cynthia_window import Window
# from .cynthia_door import Door
from ...utils import obj_clear_data, Logger


LG = Logger(__name__)
def update_building(self, context):
    """Update building geometry

    This function is used by all properties as an update callback.
    It must handle all the update and regeneration of active building object
    geometry

    Arguments:
        self     -- the property group containing the property that
                    was changed/updated
        context  -- current blender context

    Returns:
        None
    """

    # Clear mesh data from active object
    obj = context.object
    obj_clear_data(obj)

    properties = obj.property_list
    for prop in properties:
        if prop.type == 'FLOORPLAN':
            Floorplan.build(True, obj)

        elif prop.type == 'FLOOR':
            Floor.build(context, True)

        elif prop.type == 'WINDOW':
            face_indices = obj['window_groups'][str(prop.id)]
            Window.build(context, face_indices, True, prop.id)

        elif prop.type == 'DOOR':
            face_indices = obj['door_groups'][str(prop.id)]
            Door.build(context, face_indices, True, prop.id)


    return None
