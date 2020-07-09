import bpy
from .road import Road
from .road_props import RoadProperty, RoadExtrudeProperty


class BTOOLS_OT_add_road(bpy.types.Operator):
    """Create road vertex outline
    """

    bl_idname = "btools.add_road"
    bl_label = "Add Road"
    bl_options = {"REGISTER", "UNDO", "PRESET"}

    props: bpy.props.PointerProperty(type=RoadProperty)

    @classmethod
    def poll(cls, context):
        return context.mode == "OBJECT"

    def execute(self, context):
        Road.build(context, self.props)
        return {"FINISHED"}

    def draw(self, context):
        self.props.draw(context, self.layout)


class BTOOLS_OT_extrude_road(bpy.types.Operator):
    """Extrude road vertex outline
    """

    bl_idname = "btools.extrude_road"
    bl_label = "Extrude Road"
    bl_options = {"REGISTER", "UNDO", "PRESET"}

    props: bpy.props.PointerProperty(type=RoadExtrudeProperty)

    @classmethod
    def poll(cls, context):
        return context.mode == "EDIT_MESH"

    def execute(self, context):
        Road.extrude(context, self.props)
        return {"FINISHED"}

    def draw(self, context):
        self.props.draw(context, self.layout)


class BTOOLS_OT_create_curve(bpy.types.Operator):
    """Create curve
    """

    bl_idname = "btools.create_curve"
    bl_label = "Create Curve"


    def execute(self, context):
        name = "curve_" + str("{:0>3}".format(len(bpy.data.objects) + 1))
        curve_data = bpy.data.curves.new(name=name, type='CURVE')
        curve_data.dimensions = '3D'
        curve_data.splines.new(type='NURBS')
        curve_obj = bpy.data.objects.new(name=name, object_data=curve_data)

        #bpy.ops.mesh.primitive_cube_add()
        #context.collection.objects.link(curve_obj)

        # Select the new object and make it active
        bpy.ops.object.select_all(action='DESELECT')
        #curve_obj.select_set(True)
        #bpy.context.view_layer.objects.active = curve_obj

        return {"CANCELLED"}
