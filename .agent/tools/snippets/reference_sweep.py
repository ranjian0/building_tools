"""Reference corpus sweep engine. Runs INSIDE the Blender session.

`bt reference generate` prepends config globals (CASES_PATH, OUT_DIR, FILTER,
IMG_W, IMG_H) and execs this file. For every case in the manifest:
clean scene -> run scenario -> apply steps -> validate -> render -> log.

Writes OUT_DIR/<case-id>/result.json + iso/front/right renders, plus index.json/index.md.
"""

import contextlib
import hashlib
import io
import json
import math
import os

import bmesh
import bpy
from mathutils import Vector

from building_tools.btools.api import FaceTarget, apply_feature
from building_tools.btools.api.core import OPTION_TYPES, options_from_dict
from building_tools.btools.api.select import select as select_faces
from building_tools.btools.api.validate import geometry_report, validate_object

IMG_SIZE = (IMG_W, IMG_H)
ISO_DIR = Vector((1.0, -1.0, 0.85)).normalized()


# ---------------------------------------------------------------- helpers

def purge_orphans():
    for block_type in (bpy.data.meshes, bpy.data.cameras, bpy.data.materials,
                       bpy.data.lights, bpy.data.images):
        for block in list(block_type):
            if block.users == 0:
                block_type.remove(block)


def clean_scene():
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o)
    purge_orphans()


def run_scenario(name):
    """Exec a scenario file, return its {"object": ..., "faces": {...}} JSON."""
    path = os.path.join(SCENARIOS_DIR, name + ".py")
    if not os.path.exists(path):
        raise RuntimeError("no scenario %r at %s" % (name, path))
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        exec(compile(open(path).read(), path, "exec"), {"__name__": "__main__"})
    for line in buf.getvalue().splitlines():
        if line.startswith("__JSON__"):
            return json.loads(line[len("__JSON__"):])
    raise RuntimeError("scenario %r produced no __JSON__ output" % name)


# -- face selection lives in lib/face_select.py (shared, world-space
#    selectors, deterministic area ordering); loaded via _load_face_select()


def apply_steps(steps, face_map):
    """Run feature steps; returns (last_result, obj, step_summaries)."""
    obj = bpy.data.objects.get((face_map or {}).get("object") or "")
    summaries = []
    last = None
    for step in steps:
        feature = step["feature"]
        options = options_from_dict(OPTION_TYPES[feature], step.get("options", {}))
        faces = step.get("faces")
        if feature == "floorplan":
            last = apply_feature(feature, options)
        else:
            if isinstance(faces, str):
                faces = select_faces(obj, faces)
            last = apply_feature(feature, options, FaceTarget(obj, faces or []))
        summaries.append({
            "feature": feature,
            "status": last.status,
            "matgroup_counts": last.matgroup_counts,
            # -- concise line only: full tracebacks embed paths/line numbers
            #    and would make baseline diffs noisy
            "errors": last.errors[:1],
            "warnings": last.warnings,
        })
        if not last.ok:
            break
        if feature == "floorplan":
            obj = bpy.data.objects[last.created_object]
    return last, obj, summaries


def geometry_hash(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    coords = sorted(tuple(round(c, 4) for c in v.co) for v in bm.verts)
    n_faces = len(bm.faces)
    bm.free()
    payload = json.dumps([coords, n_faces]).encode()
    return hashlib.sha256(payload).hexdigest()[:16]


# -- per-matgroup render palette: distinct colors make features visible and
#    matgroup mistakes obvious; untagged faces render bright red
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
FALLBACK_COLOR = (0.50, 0.50, 0.50)


def assign_matgroup_materials(obj):
    """Give every face a flat material by its material group (render aid)."""
    me = obj.data
    me.materials.clear()
    mats = {}
    default = bpy.data.materials.new("ref_default")
    me.materials.append(default)
    default_idx = 0

    def mat_for(name, color):
        if name not in mats:
            m = bpy.data.materials.new("ref_" + name)
            # -- materials have a node tree by default; workbench MATERIAL
            #    mode reads the viewport display color, not the nodes
            m.diffuse_color = (*color, 1.0)
            bsdf = next((n for n in m.node_tree.nodes
                         if n.type == "BSDF_PRINCIPLED"), None)
            if bsdf:
                bsdf.inputs["Base Color"].default_value = (*color, 1.0)
                bsdf.inputs["Roughness"].default_value = 0.9
            me.materials.append(m)
            mats[name] = len(me.materials) - 1
        return mats[name]

    group_names = [mt.name for mt in getattr(obj, "bt_materials", [])]
    layer = me.attributes.get(".bt_material_group_index")
    if layer is None:
        return  # everything stays default; nothing tagged yet

    total = len(me.polygons)
    vals = [0] * total
    layer.data.foreach_get("value", vals)
    for i, g in enumerate(vals):
        if 0 <= g < len(group_names):
            me.polygons[i].material_index = mat_for(
                group_names[g], MATGROUP_COLORS.get(group_names[g], FALLBACK_COLOR))
        else:
            me.polygons[i].material_index = mat_for(
                "untagged_%d" % g, UNTAGGED_COLOR)


VIEW_DIRECTIONS = {
    "": Vector((1.0, -1.0, 0.85)).normalized(),   # iso
    "-front": Vector((0.0, -1.0, 0.0)),           # elevation: sees -Y face
    "-right": Vector((1.0, 0.0, 0.0)),            # elevation: sees +X face
}


def render_case(obj, case_dir, case_id):
    """Deterministic renders: workbench FLAT (iso/front/right) + EEVEE material."""
    assign_matgroup_materials(obj)

    corners = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    mins = Vector((min(c.x for c in corners), min(c.y for c in corners), min(c.z for c in corners)))
    maxs = Vector((max(c.x for c in corners), max(c.y for c in corners), max(c.z for c in corners)))
    center = (mins + maxs) / 2
    radius = max((maxs - mins).length / 2, 0.5)

    scene = bpy.context.scene
    cam_data = bpy.data.cameras.new("ref_cam")
    cam_data.type = "ORTHO"
    cam = bpy.data.objects.new("ref_cam", cam_data)
    scene.collection.objects.link(cam)

    # -- render settings once; camera moved per view
    scene.camera = cam
    scene.render.engine = "BLENDER_WORKBENCH"
    shading = scene.display.shading
    # -- attr renamed between blender versions (lighting -> light)
    if hasattr(shading, "lighting"):
        shading.lighting = "FLAT"
    elif hasattr(shading, "light"):
        shading.light = "FLAT"
    shading.color_type = "MATERIAL"
    shading.show_cavity = True
    scene.render.resolution_x, scene.render.resolution_y = IMG_SIZE
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = False
    scene.render.image_settings.file_format = "PNG"

    aspect = IMG_W / IMG_H

    # -- ensure basic lighting for EEVEE material render
    if not any(o.type == "LIGHT" for o in scene.objects):
        sun_data = bpy.data.lights.new("ref_sun", type="SUN")
        sun_data.energy = 3.0
        sun = bpy.data.objects.new("ref_sun", sun_data)
        scene.collection.objects.link(sun)
        sun.rotation_euler = (0.8, 0.2, 0.5)

    for suffix, direction in VIEW_DIRECTIONS.items():
        cam.location = center + direction * (radius * 4 + 1)
        # -- to_track_quat aims -Z along the given vector: it must point from
        #    the camera TOWARD the target, not outward
        look = (center - cam.location).normalized()
        cam.rotation_euler = look.to_track_quat("-Z", "Y").to_euler()
        bpy.context.view_layer.update()

        # -- fit: project bbox corners into camera space, cover both axes
        inv = cam.matrix_world.inverted()
        pts = [inv @ c for c in corners]
        w = max(p.x for p in pts) - min(p.x for p in pts)
        h = max(p.y for p in pts) - min(p.y for p in pts)
        cam_data.ortho_scale = max(w, h * aspect) * 1.15

        scene.render.filepath = os.path.join(
            case_dir, "image%s.png" % suffix)
        bpy.ops.render.render(write_still=True)

    # -- EEVEE material render (iso view, shows PBR/transmission/glass)
    scene.render.engine = "BLENDER_EEVEE"
    cam.location = center + VIEW_DIRECTIONS[""] * (radius * 4 + 1)
    look = (center - cam.location).normalized()
    cam.rotation_euler = look.to_track_quat("-Z", "Y").to_euler()
    bpy.context.view_layer.update()
    inv = cam.matrix_world.inverted()
    pts = [inv @ c for c in corners]
    w = max(p.x for p in pts) - min(p.x for p in pts)
    h = max(p.y for p in pts) - min(p.y for p in pts)
    cam_data.ortho_scale = max(w, h * aspect) * 1.15
    scene.render.filepath = os.path.join(case_dir, "image-material.png")
    bpy.ops.render.render(write_still=True)
    scene.render.engine = "BLENDER_WORKBENCH"

    scene.collection.objects.unlink(cam)
    bpy.data.objects.remove(cam)
    purge_orphans()


# ---------------------------------------------------------------- sweep

def run_case(case, retries=1):
    attempt = 0
    while True:
        entry = _run_case_once(case)
        if entry["error"] is None or attempt >= retries:
            return entry
        attempt += 1
        entry["retried"] = True
        print("[sweep]   retry %d for %s (previous error: %s)"
              % (attempt, case["id"], entry["error"][:60]))
        # fall through and rerun


def _run_case_once(case):
    clean_scene()
    face_map = {}
    if case.get("scenario"):
        face_map = run_scenario(case["scenario"]) or {}

    steps = case.get("steps", [])
    step_summaries = []
    obj = None
    error = None
    if case.get("preset"):
        from building_tools.btools.api.presets import PRESETS, build_preset

        try:
            res = build_preset(PRESETS[case["preset"]])
            obj = bpy.data.objects.get(res.created_object or "")
            step_summaries.append({
                "feature": "preset:" + case["preset"],
                "status": res.status,
                "matgroup_counts": res.matgroup_counts,
                "errors": res.errors[:1],
                "warnings": res.warnings[:2],
            })
            if not res.ok:
                error = "preset failed: %s" % res.status
        except Exception as exc:  # noqa: BLE001 -- sweep must continue
            error = "%s: %s" % (type(exc).__name__, exc)
    elif steps:
        try:
            last, obj, step_summaries = apply_steps(steps, face_map)
            if not last.ok:
                error = "step failed: %s" % last.status
        except Exception as exc:  # noqa: BLE001 -- sweep must continue
            error = "%s: %s" % (type(exc).__name__, exc)
    else:
        obj_name = face_map.get("object")
        obj = bpy.data.objects.get(obj_name) if obj_name else None
        if obj is None:
            error = "scenario produced no object"

    entry = {
        "id": case["id"],
        "scenario": case.get("scenario"),
        "steps": [
            {"feature": s["feature"], "options": s.get("options", {}), "faces": s.get("faces")}
            for s in steps
        ],
        "step_results": step_summaries,
        "known_issues": case.get("known_issues", []),
        "error": error,
    }

    if obj is not None and error is None:
        zs = [v.co.z for v in obj.data.vertices]
        entry["mesh"] = {
            "verts": len(obj.data.vertices),
            "edges": len(obj.data.edges),
            "faces": len(obj.data.polygons),
            "z_range": [round(min(zs), 3), round(max(zs), 3)] if zs else [0, 0],
        }
        entry["geometry_hash"] = geometry_hash(obj)
        entry["validation"] = validate_object(
            obj,
            expect=case.get("expect"),
            include_geometry=False,
        )
        entry["geometry_report"] = geometry_report(obj)
        try:
            # -- apply default BT_ materials so material bugs surface here
            from building_tools.btools.building.default_materials import (
                apply_default_materials,
            )
            apply_default_materials(obj)
            render_case(obj, os.path.join(OUT_DIR, case["id"]), case["id"])
            entry["images"] = ["image.png", "image-front.png", "image-right.png"]
        except Exception as exc:  # noqa: BLE001
            entry["images"] = []
            entry["error"] = "render/materials failed: %s" % exc
    else:
        entry["mesh"] = None
        entry["geometry_hash"] = None
        entry["validation"] = None
        entry["geometry_report"] = None
        entry["images"] = []

    import building_tools

    entry["environment"] = {
        "blender": bpy.app.version_string,
        "addon_version": ".".join(str(x) for x in building_tools.bl_info.get("version", ())),
    }
    return entry


def main():
    import fnmatch
    import importlib.util

    spec = importlib.util.spec_from_file_location("ref_cases", CASES_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    cases = mod.CASES

    if FILTER:
        cases = [c for c in cases if fnmatch.fnmatch(c["id"], FILTER)]

    os.makedirs(OUT_DIR, exist_ok=True)
    index = []
    for i, case in enumerate(cases):
        entry = run_case(case)
        case_dir = os.path.join(OUT_DIR, case["id"])
        os.makedirs(case_dir, exist_ok=True)
        with open(os.path.join(case_dir, "result.json"), "w") as f:
            json.dump(entry, f, indent=2, sort_keys=True)
        status = entry["error"] or ("ok" if entry.get("validation", {}).get("ok") else "contract violated")
        index.append({
            "id": entry["id"],
            "status": status,
            "geometry_hash": entry.get("geometry_hash"),
            "faces": (entry.get("mesh") or {}).get("faces"),
            "problems": (entry.get("validation") or {}).get("problems", []),
            "known_issues": entry.get("known_issues", []),
            "images": entry.get("images", []),
        })
        print("[sweep] %d/%d %-32s %s" % (i + 1, len(cases), entry["id"], status))

    # -- merge with the existing index so filtered runs don't clobber the
    #    cases that were not part of this run
    index_path = os.path.join(OUT_DIR, "index.json")
    if FILTER and os.path.exists(index_path):
        with open(index_path) as f:
            by_id = {c["id"]: c for c in json.load(f).get("cases", [])}
        for c in index:
            by_id[c["id"]] = c
        index = [by_id[k] for k in sorted(by_id, key=lambda s: (len(s), s))]

    with open(os.path.join(OUT_DIR, "index.json"), "w") as f:
        json.dump({"image_size": list(IMG_SIZE), "cases": index}, f, indent=2, sort_keys=True)

    # -- human-browsable gallery
    lines = ["# Reference corpus", "",
             "image size: %dx%d -- %d cases (iso / front / right)" % (IMG_W, IMG_H, len(cases)), ""]
    for e in index:
        lines.append("## %s" % e["id"])
        lines.append("")
        lines.append("- status: `%s`" % e["status"])
        lines.append("- faces: %s -- geometry_hash: `%s`" % (e["faces"], e["geometry_hash"]))
        if e["problems"]:
            lines.append("- problems: %s (known: %s)" % (e["problems"], e["known_issues"]))
        if e.get("images"):
            lines.append("")
            for img in e["images"]:
                lines.append("![%s %s](%s/%s)" % (e["id"], img, e["id"], img))
        lines.append("")
    with open(os.path.join(OUT_DIR, "index.md"), "w") as f:
        f.write("\n".join(lines))

    # -- 'failed' = hard errors only; contract violations are expected states
    #    for cases carrying known_issues markers (they gate the diff)
    failed = [e["id"] for e in index if e["status"] == "error"]
    violations = [e["id"] for e in index if e["status"] == "contract violated"]
    print("__JSON__" + json.dumps({
        "generated": len(index),
        "out_dir": OUT_DIR,
        "failed": failed,
        "violations": violations,
    }))


main()
