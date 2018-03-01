import bpy
import bmesh

from .util_mesh import make_mesh


def make_object(name, data=None):
    """ Make new object data """
    return bpy.data.objects.new(name, data)


def bm_from_obj(obj):
    """ Create bmesh from object data """
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    return bm


def bm_to_obj(bm, obj):
    """ Write bmesh to object data"""
    m = make_mesh("bm.gen_mesh")
    bm.to_mesh(m)
    obj.data = m


def link_obj(obj):
    """ Link object to active scene """
    bpy.context.scene.objects.link(obj)
    bpy.context.scene.objects.active = obj
    obj.select = True
    obj.location = bpy.context.scene.cursor_location

def obj_clear_data(obj):
    """ Removes mesh geometry data from obj """
    bm = bm_from_obj(obj)
    bmesh.ops.delete(bm, geom=list(bm.verts), context=1)
    bm_to_obj(bm, obj)
