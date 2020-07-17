import math

import bmesh
import bpy
from mathutils import Matrix

from .road_types import create_road
from ...utils import (
    link_obj,
    bm_to_obj,
    crash_safe,
    bm_from_obj,
    create_mesh,
    create_object,
)


class Road:
    @classmethod
    @crash_safe
    def build(cls, context, prop):
        """ Create road object
        """
        name = "road_" + str("{:0>3}".format(len(bpy.data.objects) + 1))
        obj = create_object(name, create_mesh(name + "_mesh"))
        link_obj(obj)
        context.view_layer.objects.active = obj

        # Create outline
        bm = bm_from_obj(obj)
        create_road(bm, prop)

        # Create curve
        cls.create_curve(context)

        # Extrude road
        cls.extrude_road(context, prop, bm)

        bm_to_obj(bm, obj)

        return obj

    @classmethod
    def create_curve(cls, context):
        # Create curve
        name = "curve_" + str("{:0>3}".format(len(bpy.data.objects) + 1))
        curve_data = bpy.data.curves.new(name=name, type='CURVE')
        curve_data.dimensions = '3D'
        spline = curve_data.splines.new(type='BEZIER')

        # Add point
        spline.bezier_points.add(1)
        spline.bezier_points[1].co = (0, 10, 0)
        spline.bezier_points[0].handle_left_type = spline.bezier_points[0].handle_right_type = "AUTO"
        spline.bezier_points[1].handle_left_type = spline.bezier_points[1].handle_right_type = "AUTO"

        # Add to scene
        curve_obj = bpy.data.objects.new(name=name, object_data=curve_data)
        curve_obj.parent = context.object
        context.collection.objects.link(curve_obj)

    @classmethod
    @crash_safe
    def extrude_road(cls, context, prop, bm):
        # Extrude once
        geom = bmesh.ops.extrude_face_region(bm, geom=bm.edges)
        verts = [e for e in geom['geom'] if isinstance(e, bmesh.types.BMVert)]

        bmesh.ops.transform(bm, matrix=Matrix.Translation((0, prop.interval, 0)),
                            verts=verts)

        if prop.extrusion_type == "STRAIGHT":
            cls.extrude_straight(context, prop, bm)
        else:
            cls.extrude_curved(context, prop, bm)

        return {"FINISHED"}

    @classmethod
    @crash_safe
    def extrude_straight(cls, context, prop, bm):
        # Add modifiers
        if not context.object.modifiers:
            # Array
            bpy.ops.object.modifier_add(type="ARRAY")
            modifier = context.object.modifiers["Array"]
            modifier.fit_type = "FIT_LENGTH"
            modifier.fit_length = prop.length
            modifier.relative_offset_displace = [0, 1, 0]

        return {"FINISHED"}

    @classmethod
    @crash_safe
    def extrude_curved(cls, context, prop, bm):
        curve = context.object.children[0]

        # Rotate vertices
        bmesh.ops.rotate(bm, matrix=Matrix.Rotation(math.radians(90.0), 3, 'Y'), verts=bm.verts)

        # Add modifiers
        if not context.object.modifiers:
            # Array
            bpy.ops.object.modifier_add(type="ARRAY")
            modifier = context.object.modifiers["Array"]
            modifier.fit_type = "FIT_CURVE"
            modifier.curve = curve
            modifier.relative_offset_displace = [0, 1, 0]

            # Curve
            bpy.ops.object.modifier_add(type="CURVE")
            modifier = context.object.modifiers["Curve"]
            modifier.object = curve
            modifier.deform_axis = "POS_Y"

        return {"FINISHED"}

    @classmethod
    @crash_safe
    def finalize_road(cls, context):
        if context.active_object is None:
            return {"FINISHED"}

        # Apply modifiers
        bpy.ops.object.modifier_apply(modifier="Array")
        bpy.ops.object.modifier_apply(modifier="Curve")

        # Remove curve
        if len(context.active_object.children) > 0 and context.active_object.children[0].type == "CURVE":
            bpy.data.objects.remove(context.active_object.children[0])

        return {"FINISHED"}
