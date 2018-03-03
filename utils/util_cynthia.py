import bpy
import bgl
from mathutils import Vector
from bpy_extras import view3d_utils


def condition(con, val1, val2):
    """ Return val1 if con is true else val2 """
    return val1 if con else val2


def ifeven(num, val1, val2):
    """ Return val1 if num is an even number else val2 """
    return condition(num % 2 == 0, val1, val2)


def kwargs_from_props(props):
    """ Converts all properties in a props into dict """
    valid_types = (
        int, float, str, tuple, bool, Vector,
        bpy.types.Material,
        bpy.types.Object
        )

    result = {}
    for p in dir(props):
        if p.startswith('__') or p in ['rna_type', 'bl_rna']:
            continue
        prop = getattr(props, p)

        if isinstance(prop, valid_types):
            result[p] = prop
        elif isinstance(prop, bpy.types.PropertyGroup) and not isinstance(prop, type(props)):
            # property group within this property
            result.update(kwargs_from_props(prop))
    return result


def assert_test(func):
    """ Catch any Exceptions that may occur in test func """

    def wrapper():
        try:
            func()
            print(func.__name__.upper() + " PASSED ..")
        except Exception as e:
            print(func.__name__.upper() + " FAILED .. :", e)

    return wrapper


def clean_scene():
    """ Delete all objects in the scene if any """
    scene = bpy.context.scene

    if scene.objects:
        active = scene.objects.active
        if active and active.mode == 'EDIT':
            bpy.ops.object.mode_set(mode='OBJECT')

        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete(use_global=False)
    return scene


def select_face_callback(self, context):
    """ Draw an outline to all selected faces """
    obj = context.object
    region = context.region
    rv3d = context.region_data
    vertices = obj.data.vertices

    bgl.glEnable(bgl.GL_BLEND)
    bgl.glColor4f(0, 0.5, 0, 1)
    bgl.glLineWidth(3)

    for fidx in self.selected_faces:
        if fidx < 0: return
        face = obj.data.polygons[fidx]
        bgl.glBegin(bgl.GL_LINE_LOOP)
        for idx in face.vertices:
            coord = vertices[idx]
            screen_pos = view3d_utils.location_3d_to_region_2d(region, rv3d, coord.co)
            bgl.glVertex2f(*screen_pos.to_tuple())
        bgl.glEnd()


def hover_face_callback(self, context):
    """ Draw an overlay on the face the mouse cursor is over """
    if self.face_index < 0: return     
    obj = context.object
    face = obj.data.polygons[self.face_index]
    vertices = obj.data.vertices
    region = context.region
    rv3d = context.region_data

    bgl.glEnable(bgl.GL_BLEND)
    bgl.glColor4f(.5, 0, 0, .4)

    bgl.glBegin(bgl.GL_POLYGON)
    for idx in face.vertices:
        coord = vertices[idx]
        screen_pos = view3d_utils.location_3d_to_region_2d(region, rv3d, coord.co)
        bgl.glVertex2f(*screen_pos.to_tuple())
    bgl.glEnd()


def ray_cast_modal(self, context, event):
    """ Set the index of the face the mouse cursor is over """

    # get the context arguments
    scene = context.scene
    region = context.region
    rv3d = context.region_data
    coord = event.mouse_region_x, event.mouse_region_y

    # get the ray from the viewport and mouse
    view_vector = view3d_utils.region_2d_to_vector_3d(region, rv3d, coord)
    ray_origin = view3d_utils.region_2d_to_origin_3d(region, rv3d, coord)

    ray_target = ray_origin + view_vector

    def obj_ray_cast(obj, matrix):
        """Wrapper for ray casting that moves the ray into object space"""

        # get the ray relative to the object
        matrix_inv = matrix.inverted()
        ray_origin_obj = matrix_inv * ray_origin
        ray_target_obj = matrix_inv * ray_target
        ray_direction_obj = ray_target_obj - ray_origin_obj

        # cast the ray
        success, location, normal, face_index = obj.ray_cast(ray_origin_obj, ray_direction_obj)

        if success:
            return location, normal, face_index
        else:
            return None, None, None

    # cast rays to find face
    hit_face = -1
    obj = context.object
    if obj.type == 'MESH':
        matrix = obj.matrix_world.copy()
        hit, normal, hit_face = obj_ray_cast(obj, matrix)
        if hit_face is None: 
            hit_face = -1
    self.face_index = hit_face
