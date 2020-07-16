import math

import bpy
import bmesh
from mathutils import Matrix

from .road_types import create_road, continuous_extrude
from ...utils import (
    link_obj,
    bm_to_obj,
    crash_safe,
    bm_from_obj,
    create_mesh,
    create_object,
    get_edit_mesh,
)


class Road:
    @classmethod
    @crash_safe
    def build(cls, context, prop):
        """ Create road object
        """
        name = "road_" + str("{:0>3}".format(len(bpy.data.objects) + 1))
        obj = create_object(name, create_mesh(name + "_mesh"))

        bm = bm_from_obj(obj)
        create_road(bm, prop)
        bm_to_obj(bm, obj)

        link_obj(obj)
        cls.create_curve(context, obj)

        return obj

    @classmethod
    def create_curve(cls, context, obj):
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
        curve_obj.parent = obj
        context.collection.objects.link(curve_obj)

    @classmethod
    @crash_safe
    def extrude(cls, context, prop):
        if prop.extrusion_type == "STRAIGHT":
            times = math.ceil(prop.length / prop.interval)
            me = get_edit_mesh()

            bm = bmesh.from_edit_mesh(me)
            continuous_extrude(bm, context, prop, bm.edges, times)
            bmesh.update_edit_mesh(me, True)
        else:
            cls.extrude_curved(context=context, prop=prop)

        return {"FINISHED"}

    @classmethod
    @crash_safe
    def extrude_curved(cls, context, prop):
        curve = context.active_object.children[0]

        # Extrude once
        me = get_edit_mesh()
        bm = bmesh.from_edit_mesh(me)
        geom = bmesh.ops.extrude_face_region(bm, geom=bm.edges)
        verts = [e for e in geom['geom'] if isinstance(e, bmesh.types.BMVert)]

        bmesh.ops.transform(bm, matrix=Matrix.Translation((0, prop.interval, 0)), space=context.object.matrix_world,
                            verts=verts)

        # Rotate vertices
        bmesh.ops.rotate(bm, matrix=Matrix.Rotation(math.radians(90.0), 3, 'Y'), verts=bm.verts)

        # Add modifiers
        if not context.object.modifiers:
            # Array
            bpy.ops.object.modifier_add(type="ARRAY")
            modifier = context.object.modifiers["Array"]
            modifier.show_on_cage = True
            modifier.fit_type = "FIT_CURVE"
            modifier.curve = curve
            modifier.relative_offset_displace = [0, 1, 0]

            # Curve
            bpy.ops.object.modifier_add(type="CURVE")
            modifier = context.object.modifiers["Curve"]
            modifier.show_on_cage = True
            modifier.show_in_editmode = True
            modifier.object = curve
            modifier.deform_axis = "POS_Y"

        return {"FINISHED"}
