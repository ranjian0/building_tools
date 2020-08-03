import bpy

from ..utils import (
    crash_safe,
    create_mesh,
    create_object,
    plane,
    bm_from_obj,
    bm_to_obj,
    link_obj,
    Matrix,
    select,
)


class Array:
    @classmethod
    @crash_safe
    def build(cls, context):
        """ Setup curved array
        """

        # Can't array nothing
        if context.active_object is None:
            return None

        # Create children
        object = context.object
        position = object.location
        curve = cls.create_curve(context)
        plane = cls.create_plane(context, curve)

        object.parent = plane
        plane.parent = curve

        # Make sure that the objects aren't offsetted from eachother
        context.scene.cursor.location = position
        select([plane, curve, object])
        bpy.ops.object.origin_clear()

        # Set location again
        curve.data.transform(matrix=Matrix.Translation(position))

        # Set up modifiers
        bpy.ops.object.modifier_add(type="ARRAY")
        modifier = context.object.modifiers["Array"]
        modifier.fit_type = "FIT_CURVE"
        modifier.curve = curve
        modifier.relative_offset_displace = [2, 0, 0]

        bpy.ops.object.modifier_add(type="CURVE")
        modifier = context.object.modifiers["Curve"]
        modifier.object = curve

        context.object.instance_type = "FACES"

        # Hide plane object
        context.object.show_instancer_for_viewport = False

    @classmethod
    def create_curve(cls, context):
        # Create curve
        name = "curve_" + str("{:0>3}".format(len(bpy.data.objects) + 1))
        curve_data = bpy.data.curves.new(name=name, type='CURVE')
        curve_data.dimensions = '3D'
        curve_data.resolution_u = 500
        spline = curve_data.splines.new(type='BEZIER')

        # Add point
        spline.bezier_points.add(1)
        spline.bezier_points[1].co = (0, 10, 0)
        spline.bezier_points[0].handle_left_type = spline.bezier_points[0].handle_right_type = "AUTO"
        spline.bezier_points[1].handle_left_type = spline.bezier_points[1].handle_right_type = "AUTO"

        # Add to scene
        curve_obj = bpy.data.objects.new(name=name, object_data=curve_data)
        context.object.parent = curve_obj
        context.collection.objects.link(curve_obj)

        return curve_obj

    @classmethod
    def create_plane(cls, context, curve):
        # Create plane
        name = "plane_" + str("{:0>3}".format(len(bpy.data.objects) + 1))
        obj = create_object(name, create_mesh(name + "_mesh"))
        bm = bm_from_obj(obj)

        plane(bm, context.active_object.dimensions.y / 2, context.active_object.dimensions.x / 2)

        bm_to_obj(bm, obj)
        link_obj(obj)
        return obj

    @classmethod
    @crash_safe
    def finalize_curved_array(cls, context):
        if context.active_object is None:
            return {"FINISHED"}

        # Apply modifiers
        bpy.ops.object.modifier_apply(modifier="Array")
        bpy.ops.object.modifier_apply(modifier="Curve")

        # Convert instances to real objects
        bpy.ops.object.duplicates_make_real()

        # Set object parent and remove other objects
        curve = context.active_object.parent
        plane = context.active_object
        object = plane.children[0]
        context.active_object.children[0].parent = None
        bpy.data.objects.remove(curve)
        bpy.data.objects.remove(plane)
        bpy.data.objects.remove(object)

        return {"FINISHED"}


class BTOOLS_OT_add_array(bpy.types.Operator):
    """Setup array
    """

    bl_idname = "btools.add_array"
    bl_label = "Add Array"
    bl_options = {"REGISTER", "UNDO", "PRESET"}

    @classmethod
    def poll(cls, context):
        return context.mode == "OBJECT"

    def execute(self, context):
        Array.build(context)
        return {"FINISHED"}


class BTOOLS_OT_finalize_array(bpy.types.Operator):
    """Apply modifiers, remove curve and remove plane
    """

    bl_idname = "btools.finalize_array"
    bl_label = "Finalize Array"
    bl_options = {"REGISTER", "UNDO", "PRESET"}

    @classmethod
    def poll(cls, context):
        return context.mode == "OBJECT"

    def execute(self, context):
        Array.finalize_curved_array(context)
        return {"FINISHED"}


classes = (BTOOLS_OT_add_array, BTOOLS_OT_finalize_array)


def register_array():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister_array():
    for cls in classes:
        bpy.utils.unregister_class(cls)
