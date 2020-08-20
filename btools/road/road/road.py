import math
from math import sin, cos

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
    add_faces_to_map,
    FaceMap,
    add_facemap_for_groups,
    filter_geom
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

        # Create outline
        bm = bm_from_obj(obj)
        vertex_count = cls.create_vertex_outline(bm, prop)

        # Create curve
        cls.create_curve(context)

        # Extrude road
        cls.extrude_road(context, prop, bm)

        bm_to_obj(bm, obj)

        # Add custom property
        obj["VertexCount"] = vertex_count

        return obj

    @classmethod
    def create_vertex_outline(cls, bm, prop):
        """Creates the original vertices
        """

        shoulder_width = sin(prop.shoulder_angle) * prop.shoulder_height
        shoulder_height = cos(prop.shoulder_angle) * prop.shoulder_height
        total_width_left = prop.width / 2

        if prop.generate_shoulders:
            total_width_left += prop.shoulder_width

        total_width_right = total_width_left
        if prop.generate_left_sidewalk:
            total_width_left += prop.sidewalk_width
        if prop.generate_right_sidewalk:
            total_width_right += prop.sidewalk_width

        # Left to right
        # Left shoulder down
        if not prop.generate_left_sidewalk:
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

        # Main road
        bm.verts.new(Vector((-prop.width / 2, 0, 0)))
        bm.verts.new(Vector((prop.width / 2, 0, 0)))

        # Right shoulder
        if prop.generate_shoulders:
            bm.verts.new(Vector((prop.width / 2 + prop.shoulder_width, 0, 0)))

            if prop.generate_right_sidewalk:
                bm.verts.new(Vector((prop.width / 2 + prop.shoulder_width, 0, prop.sidewalk_height)))
        else:
            if prop.generate_right_sidewalk:
                bm.verts.new(Vector((prop.width / 2, 0, prop.sidewalk_height)))

        # Left sidewalk top
        if prop.generate_right_sidewalk:
            bm.verts.new(Vector((total_width_right, 0, prop.sidewalk_height)))

        # Left shoulder down
        if not prop.generate_right_sidewalk:
            bm.verts.new(Vector((total_width_right + shoulder_width, 0, -shoulder_height)))

        # Generate edges
        bm.verts.ensure_lookup_table()
        for i in range(len(bm.verts) - 1):
            bm.edges.new((bm.verts[i], bm.verts[i + 1]))

        # Return amount of vertices per ring
        return len(bm.verts)

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
        curve_obj.parent = context.object
        context.collection.objects.link(curve_obj)

    @classmethod
    @crash_safe
    def extrude_road(cls, context, prop, bm):
        # Extrude once
        geom = bmesh.ops.extrude_face_region(bm, geom=bm.edges)
        verts = filter_geom(geom["geom"], bmesh.types.BMVert)

        bmesh.ops.transform(bm, matrix=Matrix.Translation((0, prop.interval, 0)),
                            verts=verts)

        # Set facemaps
        # Face order is totally random, vertex and edge order is not so get the faces from the edges
        bm.faces.layers.face_map.verify()

        groups = [FaceMap.ROAD]

        if prop.generate_left_sidewalk or prop.generate_right_sidewalk:
            groups.append(FaceMap.SIDEWALK)
            groups.append(FaceMap.SIDEWALK_SIDE)

        if not prop.generate_left_sidewalk or not prop.generate_right_sidewalk:
            groups.append(FaceMap.SHOULDER_EXTENSION)

        if prop.generate_shoulders:
            groups.append(FaceMap.SHOULDER)

        add_facemap_for_groups(groups)
        bm.edges.ensure_lookup_table()

        # Left side of road
        if not prop.generate_left_sidewalk:
            add_faces_to_map(bm, (bm.edges[0].link_faces[0],), FaceMap.SHOULDER_EXTENSION)
            face_count = 1

            if prop.generate_shoulders:
                add_faces_to_map(bm, (bm.edges[1].link_faces[0],), FaceMap.SHOULDER)
                face_count += 1
        else:
            add_faces_to_map(bm, (bm.edges[0].link_faces[0],), FaceMap.SIDEWALK)
            add_faces_to_map(bm, (bm.edges[1].link_faces[0],), FaceMap.SIDEWALK_SIDE)
            face_count = 2

            if prop.generate_shoulders:
                add_faces_to_map(bm, (bm.edges[2].link_faces[0],), FaceMap.SHOULDER)
                face_count += 1

        # Central road
        add_faces_to_map(bm, (bm.edges[face_count].link_faces[0],), FaceMap.ROAD)
        face_count += 1

        # Right side of road
        if prop.generate_shoulders:
            add_faces_to_map(bm, (bm.edges[face_count].link_faces[0],), FaceMap.SHOULDER)
            face_count += 1

        if prop.generate_right_sidewalk:
            add_faces_to_map(bm, (bm.edges[face_count].link_faces[0],), FaceMap.SIDEWALK_SIDE)
            add_faces_to_map(bm, (bm.edges[face_count + 1].link_faces[0],), FaceMap.SIDEWALK)
        else:
            add_faces_to_map(bm, (bm.edges[face_count].link_faces[0],), FaceMap.SHOULDER_EXTENSION)

        # Continue to extrude
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

        # Uv calculations
        bm = bm_from_obj(context.active_object)
        count = int(context.active_object["VertexCount"])
        uv_layer = bm.loops.layers.uv.new()
        sections = len(bm.verts) // count
        total_distance = 0

        uv_coords = []

        bm.verts.ensure_lookup_table()
        bm.verts.index_update()
        last_position = (bm.verts[0].co + bm.verts[count].co) / 2  # Calculate center of road
        texture_scale = 0.1

        # Calculate uvs for all vertices
        for i in range(sections):
            current_position = (bm.verts[i * count].co + bm.verts[(i + 1) * count - 1].co) / 2  # Calculate center of road
            total_distance += (last_position - current_position).length

            for j in range(count):
                uv_coords.append((j % 2, total_distance * texture_scale))

            last_position = current_position

        # Set uvs
        for f in bm.faces:
            for l in f.loops:
                if l.vert.index < len(uv_coords):
                    l[uv_layer].uv = uv_coords[l.vert.index]

        bm_to_obj(bm, context.active_object)

        return {"FINISHED"}
