from .door import Door
from ...utils import (
        facedata_from_index,
        Template_Modal_OP)


class DoorOperator(Template_Modal_OP):
    """ Creates doors on selected mesh faces """
    bl_idname = "cynthia.add_door"
    bl_label = "Add Door"
    bl_options = {'REGISTER'}

    def modal_setup(self, context, event):

        # Add window property
        obj     = context.object
        prop    = obj.property_list[obj.property_index]

        data = obj['door_groups'][str(prop.id)]
        if not isinstance(data, list):
            data = data.to_list()
        face_data = facedata_from_index(obj, self.face_index)
        data.append(face_data)
        obj['door_groups'].update({str(prop.id) : data})

        # Create geometry
        Door.build(context, [self.face_index])

    def invoke_setup(self, context, event):

        # Add property proxy
        obj         = context.object
        prop        = obj.property_list.add()
        door        = obj.building.doors.add()
        prop.type   = "DOOR"
        prop.id     = len(obj.building.doors)-1
        prop.name   = "Door Property {}".format(len(obj.building.doors))
        obj.property_index          = len(obj.property_list)-1

        # Store face indices for each door property
        if not obj.get('door_groups'):
            obj['door_groups']            = dict()
        obj['door_groups'][str(prop.id)]  = list()

