from .window import Window
from ...utils import (
        facedata_from_index,
        Template_Modal_OP)


class WindowOperator(Template_Modal_OP):
    """ Creates windows on selected mesh faces """
    bl_idname = "cynthia.add_window"
    bl_label = "Add Window"
    bl_options = {'REGISTER'}

    def modal_setup(self, context, event):

        # Add window property
        obj     = context.object
        prop    = obj.property_list[obj.property_index]

        data = obj['window_groups'][str(prop.id)]
        if not isinstance(data, list):
            data = data.to_list()
        face_data = facedata_from_index(obj, self.face_index)
        data.append(face_data)
        obj['window_groups'].update({str(prop.id) : data})

        # Create geometry
        Window.build(context, [self.face_index])

    def invoke_setup(self, context, event):

        # Add property proxy
        obj         = context.object
        prop        = obj.property_list.add()
        win         = obj.building.windows.add()
        prop.type   = "WINDOW"
        prop.id     = len(obj.building.windows)-1
        prop.name   = "Window Property {}".format(len(obj.building.windows))
        obj.property_index          = len(obj.property_list)-1

        # Store face indices for each window property
        if not obj.get('window_groups'):
            obj['window_groups']            = dict()
        obj['window_groups'][str(prop.id)]  = list()

