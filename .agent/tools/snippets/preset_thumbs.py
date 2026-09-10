"""Render a thumbnail for each building preset.

Run inside the session (via `bt exec`): builds every preset and renders a
canonical iso workbench view to <repo>/btools/presets/thumbs/<id>.png.
"""

import os

import bmesh
import bpy
from mathutils import Vector

from building_tools.btools.api.presets import PRESETS, build_preset
from building_tools.btools.api.select import select as select_faces
from building_tools.btools.api.validate import validate_object

OUT_DIR = THUMBS_DIR
ISO_DIR = Vector((1.0, -1.0, 0.85)).normalized()
SIZE = (256, 176)

MATGROUP_COLORS = {
    "walls": (0.66, 0.63, 0.59),
    "slabs": (0.52, 0.52, 0.55),
    "columns": (0.60, 0.60, 0.62),
    "roof": (0.60, 0.27, 0.19),
    "roof_hangs": (0.42, 0.19, 0.14),
    "door": (0.43, 0.27, 0.12),
    "door_panels": (0.56, 0.37, 0.19),
    "door_panes": (0.56, 0.37, 0.19),
    "door_louvers": (0.56, 0.37, 0.19),
    "frame": (0.13, 0.13, 0.14),
    "window": (0.42, 0.65, 0.82),
    "window_bars": (0.13, 0.13, 0.14),
    "window_panes": (0.56, 0.76, 0.88),
    "window_louvers": (0.56, 0.76, 0.88),
    "balcony": (0.78, 0.64, 0.28),
    "railing_posts": (0.25, 0.25, 0.28),
    "railing_walls": (0.36, 0.39, 0.43),
    "railing_rails": (0.25, 0.25, 0.28),
    "stairs": (0.63, 0.56, 0.46),
    "custom": (0.65, 0.45, 0.65),
}
UNTAGGED_COLOR = (0.90, 0.10, 0.10)


def clean_scene():
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o)
    for block in (bpy.data.meshes, bpy.data.cameras, bpy.data.materials):
        for item in list(block):
            if item.users == 0:
                block.remove(item)


def assign_materials(obj):
    me = obj.data
    me.materials.clear()
    default = bpy.data.materials.new("thumb_default")
    me.materials.append(default)

    def mat_for(name, color):
        m = bpy.data.materials.new("thumb_" + name)
        m.diffuse_color = (*color, 1.0)
        me.materials.append(m)
        return len(me.materials) - 1

    group_names = [mt.name for mt in getattr(obj, "bt_materials", [])]
    layer = me.attributes.get(".bt_material_group_index")
    if layer is None:
        return
    vals = [0] * len(me.polygons)
    layer.data.foreach_get("value", vals)
    for i, g in enumerate(vals):
        if 0 <= g < len(group_names):
            me.polygons[i].material_index = mat_for(
                group_names[g], MATGROUP_COLORS.get(group_names[g], (0.5, 0.5, 0.5)))
        else:
            me.polygons[i].material_index = mat_for("untagged", UNTAGGED_COLOR)


def render(obj, path):
    scene = bpy.context.scene
    cam_data = bpy.data.cameras.new("thumb_cam")
    cam_data.type = "ORTHO"
    cam = bpy.data.objects.new("thumb_cam", cam_data)
    scene.collection.objects.link(cam)

    corners = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    mins = Vector((min(c.x for c in corners), min(c.y for c in corners), min(c.z for c in corners)))
    maxs = Vector((max(c.x for c in corners), max(c.y for c in corners), max(c.z for c in corners)))
    center = (mins + maxs) / 2
    radius = max((maxs - mins).length / 2, 0.5)

    cam.location = center + ISO_DIR * (radius * 4 + 1)
    look = (center - cam.location).normalized()
    cam.rotation_euler = look.to_track_quat("-Z", "Y").to_euler()
    bpy.context.view_layer.update()
    inv = cam.matrix_world.inverted()
    pts = [inv @ c for c in corners]
    w = max(p.x for p in pts) - min(p.x for p in pts)
    h = max(p.y for p in pts) - min(p.y for p in pts)
    cam_data.ortho_scale = max(w, h * SIZE[0] / SIZE[1]) * 1.15

    scene.camera = cam
    scene.render.engine = "BLENDER_WORKBENCH"
    shading = scene.display.shading
    if hasattr(shading, "lighting"):
        shading.lighting = "STUDIO"
    elif hasattr(shading, "light"):
        shading.light = "STUDIO"
    shading.color_type = "MATERIAL"
    shading.show_cavity = False
    scene.render.resolution_x, scene.render.resolution_y = SIZE
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = False
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)

    scene.collection.objects.unlink(cam)
    bpy.data.objects.remove(cam)


def main():
    os.makedirs(THUMBS_DIR, exist_ok=True)
    for pid, preset in PRESETS.items():
        clean_scene()
        res = build_preset(preset)
        obj = bpy.data.objects.get(res.created_object or "")
        status = res.status
        if obj is not None:
            assign_materials(obj)
            try:
                render(obj, os.path.join(THUMBS_DIR, pid + ".png"))
            except Exception as exc:  # noqa: BLE001
                status = "render failed: %s" % exc
        report = validate_object(obj, include_geometry=False) if obj else {"ok": False}
        print("[thumbs] %-22s %s (contract ok=%s)" % (pid, status, report["ok"]))


main()
