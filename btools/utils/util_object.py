from contextlib import contextmanager

import bmesh
import bpy

from .util_mesh import select, get_edit_mesh


def create_object(name, data=None):
    """ Make new object data
    """
    return bpy.data.objects.new(name, data)


def bm_from_obj(obj):
    """ Create bmesh from object data
    """
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    return bm


def bm_to_obj(bm, obj):
    """ Write bmesh to object data
    """
    bm.to_mesh(obj.data)
    bm.free()


def link_obj(obj):
    """ Link object to active scene
    """
    bpy.context.scene.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    select(bpy.context.view_layer.objects, False)
    obj.select_set(True)
    obj.location = bpy.context.scene.cursor.location


def obj_clear_data(obj):
    """ Removes mesh geometry data from obj
    """
    bm = bm_from_obj(obj)
    bmesh.ops.delete(bm, geom=list(bm.verts), context=1)
    bm_to_obj(bm, obj)


@contextmanager
def bmesh_from_active_object(context=None):
    context = context or bpy.context

    if context.mode == "EDIT_MESH":
        me = get_edit_mesh()
        bm = bmesh.from_edit_mesh(me)
    elif context.mode == "OBJECT":
        bm = bm_from_obj(context.object)

    yield bm

    if context.mode == "EDIT_MESH":
        bmesh.update_edit_mesh(me, True)
    elif context.mode == "OBJECT":
        bm_to_obj(bm, context.object)
