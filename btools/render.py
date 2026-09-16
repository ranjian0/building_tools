"""Headless confirmation renders (roadmap: pip-package phase 4).

Sets up an orthographic camera + a small lighting rig over the current
scene's mesh bounds and renders a PNG. Works with the pip bpy wheel:
engines are tried in order until one works (EEVEE needs a GPU; Workbench
and Cycles-CPU render anywhere).
"""

import math
import os

import bpy
from mathutils import Vector

_ENGINE_FALLBACK = (
    "BLENDER_EEVEE_NEXT",
    "BLENDER_EEVEE",
    "BLENDER_WORKBENCH",
    "CYCLES",
)

_VIEWS = ("front", "right", "top", "iso")


def _scene_bounds():
    """(min, max) world corners over all mesh objects."""
    lo = Vector((math.inf,) * 3)
    hi = Vector((-(math.inf),) * 3)
    found = False
    for obj in bpy.data.objects:
        if obj.type != "MESH" or not obj.data.vertices:
            continue
        found = True
        for corner in obj.bound_box:
            world = obj.matrix_world @ Vector(corner)
            lo = Vector(map(min, lo, world))
            hi = Vector(map(max, hi, world))
    if not found:
        lo, hi = Vector((-5.0, -5.0, 0.0)), Vector((5.0, 5.0, 10.0))
    return lo, hi


def _pick_engine(scene, requested=None):
    candidates = [requested] if requested else []
    candidates += [e for e in _ENGINE_FALLBACK if e not in candidates]
    for engine in candidates:
        try:
            scene.render.engine = engine
            return engine
        except TypeError:
            continue
    return scene.render.engine  # last resort: whatever is set


def _aim(cam, direction, distance):
    """Place the camera `distance` back along -direction and aim it."""
    cam.location = cam.location - direction.normalized() * distance
    forward = direction.normalized()
    cam.rotation_euler = forward.to_track_quat("-Z", "Y").to_euler()


def setup_camera(scene, view="iso", margin=1.15):
    lo, hi = _scene_bounds()
    center = (lo + hi) / 2
    diag = (hi - lo).length or 10.0
    dist = diag * margin

    cam_data = bpy.data.cameras.new("btools_render_cam")
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = max(hi.x - lo.x, hi.y - lo.y, 1.0) * margin
    cam_data.clip_start = 0.01
    cam_data.clip_end = dist * 4.0
    cam = bpy.data.objects.new("btools_render_cam", cam_data)
    scene.collection.objects.link(cam)

    dirs = {
        "front": Vector((0.0, -1.0, 0.15)),
        "right": Vector((1.0, 0.0, 0.15)),
        "top": Vector((0.0, -0.001, 1.0)),
        "iso": Vector((1.0, -1.0, 0.85)),
    }
    direction = dirs.get(view, dirs["iso"])
    cam.location = center + direction.normalized() * dist
    aim = (center - cam.location).normalized()
    cam.rotation_euler = aim.to_track_quat("-Z", "Y").to_euler()
    scene.camera = cam
    return cam


def setup_lighting(scene):
    sun_data = bpy.data.lights.new("btools_sun", type="SUN")
    sun_data.energy = 3.0
    sun = bpy.data.objects.new("btools_sun", sun_data)
    sun.rotation_euler = (math.radians(50.0), 0.0, math.radians(30.0))
    scene.collection.objects.link(sun)

    fill_data = bpy.data.lights.new("btools_fill", type="AREA")
    fill_data.energy = 1e5
    fill_data.size = 10.0
    fill = bpy.data.objects.new("btools_fill", fill_data)
    lo, hi = _scene_bounds()
    fill.location = (lo + hi) / 2 + Vector((0.0, -hi.y, (hi.z - lo.z) * 1.5))
    scene.collection.objects.link(fill)


def render(path, engine=None, view="iso", resolution=(1280, 1280)):
    """Render the current scene to `path`. Returns (engine_used, path).

    Engines are tried in order until one works; EEVEE needs a GPU,
    Workbench renders anywhere."""
    scene = bpy.context.scene
    used = _pick_engine(scene, engine)

    # -- purge previous render helpers so repeated calls stay clean
    for name in ("btools_render_cam", "btools_sun", "btools_fill"):
        old = bpy.data.objects.get(name)
        if old is not None:
            bpy.data.objects.remove(old, do_unlink=True)

    setup_camera(scene, view)
    setup_lighting(scene)

    scene.render.resolution_x, scene.render.resolution_y = resolution
    scene.render.image_settings.file_format = "PNG"
    path = os.path.abspath(path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    return used, path


def render_views(base_path, views=_VIEWS, engine=None, resolution=(1280, 1280)):
    """Render multiple views: base_path 'out.png' -> out.front.png etc."""
    base, ext = os.path.splitext(base_path)
    ext = ext or ".png"
    out = []
    for view in views:
        used, path = render(
            f"{base}.{view}{ext}", engine=engine, view=view, resolution=resolution
        )
        out.append((view, used, path))
    return out
