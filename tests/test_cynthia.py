# =======================================================
#
#           TESTS MODULE
#
# =======================================================

"""
Not the best way to test things 
    - But it works
    - Care must be taken as most of the functions require
      different contexts and setups
    - comment the last line in each test to see what it does

"""
import bpy
from ..cynthia_floorplan import Floorplan
from ..cynthia_floor import Floor
from ..cynthia_window import Window
from mathutils import Vector
from ..utils import (
    assert_test,
    clean_scene,
    make_mesh,
    make_object,
    bm_from_obj,
    bm_to_obj)


class CynthiaTest:

    @classmethod
    def run_tests(cls):
        """ Run all tests """

        # --test floorplan
        test_floorplan()

        # --test floors
        test_floors()

        # -- test_window
        test_window()


@assert_test
def test_floorplan():
    scene = clean_scene()
    fp = Floorplan(None)

    me = make_mesh("empty")
    test_fp = make_object("test_floorplan", me)
    bm = bm_from_obj(test_fp)
    fp.make_circular(bm, 2, 32, False)
    bm_to_obj(bm, test_fp)

    test_fp1 = make_object("test_floorplan1", me)
    bm = bm_from_obj(test_fp1)
    fp.make_composite(bm, 2, 2, 1, 2, 3, 4)
    bm_to_obj(bm, test_fp1)

    test_fp2 = make_object("test_floorplan2", me)
    bm = bm_from_obj(test_fp2)
    fp.make_hshaped(bm, 3, 3, 4, 2, 1, 2, 1, 2, 1, 9)
    bm_to_obj(bm, test_fp2)

    scene.objects.link(test_fp)
    scene.objects.link(test_fp1)
    scene.objects.link(test_fp2)
    _ = clean_scene()


@assert_test
def test_floors():
    scene = clean_scene()
    fp = Floorplan(None)
    floor = Floor(None)

    me = make_mesh("empty")
    test_fp = make_object("test_floorplan", me)
    bm = bm_from_obj(test_fp)
    fp.make_composite(bm, 2, 2, 1, 2, 3, 4)
    bm_to_obj(bm, test_fp)

    scene.objects.link(test_fp)
    scene.objects.active = test_fp
    test_fp.select = True
    bpy.ops.object.mode_set(mode='EDIT')
    floor.make_floors()
    bpy.ops.object.mode_set(mode='OBJECT')
    _ = clean_scene()


@assert_test
def test_window():
    scene = clean_scene()
    win = Window(None)

    bpy.ops.mesh.primitive_cube_add(view_align=False, enter_editmode=False, location=(0, 0, 0), layers=(
        True, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False,
        False, False, False, False))
    bpy.ops.transform.resize(value=(4, 4, 4), constraint_axis=(True, True, True), constraint_orientation='GLOBAL',
                             mirror=False, proportional='DISABLED', proportional_edit_falloff='SMOOTH',
                             proportional_size=1)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.transform.translate(value=(0, 0, 2), constraint_axis=(False, False, True), constraint_orientation='GLOBAL',
                                mirror=False, proportional='DISABLED', proportional_edit_falloff='SMOOTH',
                                proportional_size=1)
    bpy.ops.mesh.select_all(action='DESELECT')
    bpy.ops.object.mode_set(mode='OBJECT')

    # Select -y normal face
    obj = scene.objects.active
    for p in obj.data.polygons:
        if p.normal == Vector((0, -1, 0)):
            p.select = True

    bpy.ops.object.mode_set(mode='EDIT')
    win.generate_type_basic()
    bpy.ops.object.mode_set(mode='OBJECT')

    # Select -y normal face
    obj = scene.objects.active
    for p in obj.data.polygons:
        if p.normal == Vector((0, 1, 0)):
            p.select = True

    bpy.ops.object.mode_set(mode='EDIT')
    win.generate_type_arched()
    bpy.ops.object.mode_set(mode='OBJECT')
    _ = clean_scene()


"""

@assert_test
def test_door():
    scene = clean_scene()

    bpy.ops.mesh.primitive_cube_add(view_align=False, enter_editmode=False, location=(0, 0, 0), layers=(
    True, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False,
    False, False, False, False))
    bpy.ops.transform.resize(value=(6, 4, 6), constraint_axis=(True, True, True), constraint_orientation='GLOBAL',
                             mirror=False, proportional='DISABLED', proportional_edit_falloff='SMOOTH',
                             proportional_size=1)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.transform.translate(value=(0, 0, 2), constraint_axis=(False, False, True), constraint_orientation='GLOBAL',
                                mirror=False, proportional='DISABLED', proportional_edit_falloff='SMOOTH',
                                proportional_size=1)
    bpy.ops.mesh.select_all(action='DESELECT')
    bpy.ops.object.mode_set(mode='OBJECT')

    # Select -y normal face
    obj = scene.objects.active
    for p in obj.data.polygons:
        if p.normal == Vector((0, -1, 0)):
            p.select = True

    bpy.ops.object.mode_set(mode='EDIT')
    door(0, 0, 0.1, 0.1, False, True, 2, 2, .05, .01, .5, 1, True, 2, 2, .05, .01, .7, 0, 2, 3, 0, 0, 0, True)
    bpy.ops.object.mode_set(mode='OBJECT')
    _ = clean_scene()


@assert_test
def test_staircase():
    scene = clean_scene()

    me = make_mesh("empty")
    test_fp = make_object("test_floorplan", me)
    bm = bm_from_obj(test_fp)
    make_stair_case(bm)
    bm_to_obj(bm, test_fp)

    scene.objects.link(test_fp)
    _ = clean_scene()


@assert_test
def test_railing():
    scene = clean_scene()

    bpy.ops.mesh.primitive_cube_add(view_align=False, enter_editmode=False, location=(0, 0, 0), layers=(
    True, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False,
    False, False, False, False))
    bpy.ops.transform.resize(value=(4, 4, 1), constraint_axis=(True, True, False), constraint_orientation='GLOBAL',
                             mirror=False, proportional='DISABLED', proportional_edit_falloff='SMOOTH',
                             proportional_size=1)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='DESELECT')
    bpy.ops.object.mode_set(mode='OBJECT')

    bm = bm_from_obj(scene.objects.active)

    maxz = max([v.co.z for v in bm.verts])
    edges = [e for e in bm.edges if set([v.co.z for v in e.verts]) == set([maxz])]

    make_railing(bm, edges[:2], .15, 1, .5, .2, .05, .2, .075, .7, .15, 2, True, True, 'RAILS')
    bm_to_obj(bm, scene.objects.active)
    _ = clean_scene()


@assert_test
def test_balcony():
    scene = clean_scene()

    bpy.ops.mesh.primitive_cube_add(view_align=False, enter_editmode=False, location=(0, 0, 0), layers=(
    True, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False,
    False, False, False, False))
    bpy.ops.transform.resize(value=(4, 4, 1), constraint_axis=(True, True, False), constraint_orientation='GLOBAL',
                             mirror=False, proportional='DISABLED', proportional_edit_falloff='SMOOTH',
                             proportional_size=1)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='DESELECT')
    bpy.ops.object.mode_set(mode='OBJECT')

    # Select -y normal face
    obj = scene.objects.active
    for p in obj.data.polygons:
        if p.normal == Vector((0, -1, 0)):
            p.select = True

    bpy.ops.object.mode_set(mode='EDIT')
    make_balcony(1, True, .15, .7, .9, .15, .025, .2, .075, .7, .15, .7, True, True, 'WALL', 2, 2, 0, 0, 0, True)
    bpy.ops.object.mode_set(mode='OBJECT')
    _ = clean_scene()


@assert_test
def test_stairs():
    scene = clean_scene()

    bpy.ops.mesh.primitive_cube_add(view_align=False, enter_editmode=False, location=(0, 0, 0), layers=(
    True, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False,
    False, False, False, False))
    bpy.ops.transform.resize(value=(4, 4, 1), constraint_axis=(True, True, False), constraint_orientation='GLOBAL',
                             mirror=False, proportional='DISABLED', proportional_edit_falloff='SMOOTH',
                             proportional_size=1)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='DESELECT')
    bpy.ops.object.mode_set(mode='OBJECT')

    # Select -y normal face
    obj = scene.objects.active
    for p in obj.data.polygons:
        if p.normal == Vector((0, -1, 0)):
            p.select = True

    bpy.ops.object.mode_set(mode='EDIT')
    make_stairs_type1()
    bpy.ops.object.mode_set(mode='OBJECT')

    obj = scene.objects.active
    for p in obj.data.polygons:
        if p.normal == Vector((0, 1, 0)):
            p.select = True

    bpy.ops.object.mode_set(mode='EDIT')
    make_stairs_type2()
    bpy.ops.object.mode_set(mode='OBJECT')
    _ = clean_scene()


@assert_test
def test_roof():
    scene = clean_scene()

    if scene.objects.active:
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.delete(use_global=False)
    bpy.ops.mesh.primitive_cube_add(radius=1, view_align=False, enter_editmode=False, location=(0, 0, 0), layers=(
    True, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False,
    False, False, False, False))
    bpy.ops.transform.resize(value=(2, 2, 2), constraint_axis=(False, False, False), constraint_orientation='GLOBAL',
                             mirror=False, proportional='DISABLED', proportional_edit_falloff='SMOOTH',
                             proportional_size=1)
    bpy.ops.object.editmode_toggle()
    bpy.ops.mesh.select_mode(use_extend=False, use_expand=False, type='FACE')
    bpy.ops.mesh.select_all(action='TOGGLE')

    me = get_edit_mesh()
    bm = bmesh.from_edit_mesh(me)

    for f in bm.faces:
        if f.normal.to_tuple() == (0, 0, 1):
            f.select = True

    make_hip_roof(bm, me)
    bmesh.update_edit_mesh(me, True)
    bpy.ops.object.mode_set(mode='OBJECT')
    _ = clean_scene()


test_floorplan()
test_floors()
test_door()
test_staircase()
test_railing()
test_balcony()
test_stairs()
test_roof()
test_window()
"""
