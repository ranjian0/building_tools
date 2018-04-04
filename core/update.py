import bpy

from ..utils import obj_clear_data, Logger


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

    # CAUTION!
    # - property_list always contains at least one prop in a valid building, this means atleast one of the
    #   if-else block will be executed.
    # - Blocks that are lower in the if-else block require that all blocks above them
    #   are executed first. eg if

    properties = obj.property_list
    for prop in properties:
        if prop.type == 'FLOORPLAN':
            from .floorplan import Floorplan
            Floorplan.build(True, obj)

        elif prop.type == 'FLOOR':
            from .floor import Floor
            Floor.build(context, True)

        elif prop.type == 'WINDOW':
            from .window import Window
            face_indices = obj['window_groups'][str(prop.id)]
            Window.build(context, face_indices, True, prop.id)

        elif prop.type == 'DOOR':
            from .door import Door
            face_indices = obj['door_groups'][str(prop.id)]
            Door.build(context, face_indices, True, prop.id)


    return None