import math
from math import sin, cos
from random import randrange, random

import bmesh
import bpy
from mathutils import Matrix, Vector

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
        face_count = cls.create_vertex_outline(bm, prop)

        # Create curve
        cls.create_curve(context)

        # Extrude road
        cls.extrude_road(context, prop, bm)

        bm_to_obj(bm, obj)

        # Add custom property
        obj["FaceCount"] = face_count

        return obj

    @classmethod
    def create_vertex_outline(cls, bm, prop):
        """Creates the original vertices
        """

        shoulder_width = sin(prop.shoulder_angle) * prop.shoulder_height
        shoulder_height = cos(prop.shoulder_angle) * prop.shoulder_height
        total_width_left = prop.width / 2
        total_width_right = 0

        if prop.generate_shoulders:
            total_width_left += prop.shoulder_width

        total_width_right = total_width_left
        if prop.generate_left_sidewalk:
            total_width_left += prop.sidewalk_width
        if prop.generate_right_sidewalk:
            total_width_right += prop.sidewalk_width

        # Left to right
        # Left shoulder down
        if not prop.generate_left_sidewalk and prop.generate_shoulders:
            bm.verts.new(Vector((-total_width_left - shoulder_width, 0, -shoulder_height)))

        # Left sidewalk top
        if prop.generate_left_sidewalk:
            bm.verts.new(Vector((-total_width_left, 0, prop.sidewalk_height)))

        # Left shoulder
        if prop.generate_shoulders:
            if prop.generate_left_sidewalk:
                bm.verts.new(Vector((-prop.width / 2 - prop.shoulder_width, 0, prop.sidewalk_height)))

            bm.verts.new(Vector((-prop.width / 2 - prop.shoulder_width, 0, 0)))
        else:
            if prop.generate_left_sidewalk:
                bm.verts.new(Vector((-prop.width / 2, 0, prop.sidewalk_height)))

            bm.verts.new(Vector((-prop.width / 2, 0, 0)))

        # Main road
        bm.verts.new(Vector((-prop.width / 2, 0, 0)))
        bm.verts.new(Vector((prop.width / 2, 0, 0)))

        # Right shoulder
        if prop.generate_shoulders:
            bm.verts.new(Vector((prop.width / 2 + prop.shoulder_width, 0, 0)))

            if prop.generate_right_sidewalk:
                bm.verts.new(Vector((prop.width / 2 + prop.shoulder_width, 0, prop.sidewalk_height)))
        else:
            bm.verts.new(Vector((prop.width / 2, 0, 0)))

            if prop.generate_right_sidewalk:
                bm.verts.new(Vector((prop.width / 2, 0, prop.sidewalk_height)))

        # Left sidewalk top
        if prop.generate_right_sidewalk:
            bm.verts.new(Vector((total_width_right, 0, prop.sidewalk_height)))

        # Left shoulder down
        if not prop.generate_right_sidewalk and prop.generate_shoulders:
            bm.verts.new(Vector((total_width_right + shoulder_width, 0, -shoulder_height)))

        # Generate edges
        bm.verts.ensure_lookup_table()
        for i in range(len(bm.verts) - 1):
            bm.edges.new((bm.verts[i], bm.verts[i + 1]))

        # Return amount of faces/edges (vertices - 1)
        return len(bm.verts) - 1


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
            modifier.show_in_editmode = True
            modifier.show_on_cage = True
            modifier.fit_type = "FIT_LENGTH"
            modifier.fit_length = prop.length
            modifier.use_merge_vertices = True
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
            modifier.use_merge_vertices = True
            modifier.curve = curve
            modifier.relative_offset_displace = [0, 1, 0]

            # Curve
            bpy.ops.object.modifier_add(type="CURVE")
            modifier = context.object.modifiers["Curve"]
            modifier.show_in_editmode = True
            modifier.show_on_cage = True
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

        # Set uvs
        bm = bm_from_obj(context.active_object)
        count = int(context.active_object["FaceCount"])
        context.active_object.data.uv_layers.new(name="Road")
        sections = int(len(bm.verts) / count)

        for i in range(sections):
            for j in range(count):
                if j % 2 == 0:
                    context.active_object.data.uv_layers.active.data[j + i * (count)].uv = (i / 2.0, 0.0)
                else:
                    context.active_object.data.uv_layers.active.data[j + i * (count)].uv = (i / 2.0, 1.0)

        return {"FINISHED"}
