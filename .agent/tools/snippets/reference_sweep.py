"""Reference corpus sweep engine. Runs INSIDE the Blender session.

`bt reference generate` prepends config globals (CASES_PATH, OUT_DIR, FILTER,
IMG_W, IMG_H) and execs this file. For every case in the manifest:
clean scene -> run scenario -> apply steps -> validate -> render -> log.

Writes OUT_DIR/<case-id>/result.json + image.png, plus index.json/index.md.
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


def select_faces(obj, selector):
    """Resolve a face selector name to live face indices."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.faces.ensure_lookup_table()
    bm.faces.index_update()
    top_z = max(f.calc_center_median().z for f in bm.faces)
    out = []
    if selector == "all":
        out = [f.index for f in bm.faces]
    elif selector == "top_face":
        cands = [f for f in bm.faces if abs(f.calc_center_median().z - top_z) < 1e-4]
        out = [max(cands, key=lambda f: f.calc_area()).index]
    elif selector in ("ground_wall", "ground_walls"):
        hits = [f.index for f in bm.faces
                if abs(f.normal.z) < 0.001 and f.calc_center_median().z < 3.0
                and f.calc_area() > 1.0]
        out = hits[:1] if selector.endswith("_wall") else hits
    elif selector in ("upper_wall", "upper_walls"):
        hits = [f.index for f in bm.faces
                if abs(f.normal.z) < 0.001 and 3.0 < f.calc_center_median().z < top_z - 0.5
                and f.calc_area() > 1.0]
        out = hits[:1] if selector.endswith("_wall") else hits
    elif selector == "front":
        out = [f.index for f in bm.faces if f.normal.y > 0.9]
    elif selector == "inner":
        inner = []
        for f in bm.faces:
            if abs(f.normal.z) >= 0.1:
                continue
            c = f.calc_center_median()
            radial = Vector((c.x, c.y)).normalized()
            if f.normal.xy.normalized().dot(radial) < -0.9:
                inner.append(f.index)
        out = inner
    else:
        raise RuntimeError("unknown face selector %r" % selector)
    bm.free()
    if not out:
        raise RuntimeError("face selector %r matched nothing" % selector)
    return out


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


def render_case(obj, path):
    """Deterministic workbench render: iso ortho camera, fixed resolution."""
    scene = bpy.context.scene

    cam_data = bpy.data.cameras.new("ref_cam")
    cam_data.type = "ORTHO"
    cam = bpy.data.objects.new("ref_cam", cam_data)
    scene.collection.objects.link(cam)

    # -- frame from world bounding box
    corners = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    mins = Vector((min(c.x for c in corners), min(c.y for c in corners), min(c.z for c in corners)))
    maxs = Vector((max(c.x for c in corners), max(c.y for c in corners), max(c.z for c in corners)))
    center = (mins + maxs) / 2
    extent = maxs - mins
    radius = max(extent.length / 2, 0.5)

    cam.location = center + ISO_DIR * (radius * 4 + 1)
    # -- to_track_quat aims -Z along the given vector: it must point from the
    #    camera TOWARD the target, not outward
    look = (center - cam.location).normalized()
    cam.rotation_euler = look.to_track_quat("-Z", "Y").to_euler()
    bpy.context.view_layer.update()

    # -- fit: project bbox corners into camera space, cover both axes
    inv = cam.matrix_world.inverted()
    pts = [inv @ c for c in corners]
    w = max(p.x for p in pts) - min(p.x for p in pts)
    h = max(p.y for p in pts) - min(p.y for p in pts)
    aspect = IMG_W / IMG_H
    cam_data.ortho_scale = max(w, h * aspect) * 1.15

    scene.camera = cam
    scene.render.engine = "BLENDER_WORKBENCH"
    shading = scene.display.shading
    # -- attr renamed between blender versions (lighting -> light)
    if hasattr(shading, "lighting"):
        shading.lighting = "STUDIO"
    elif hasattr(shading, "light"):
        shading.light = "STUDIO"
    shading.color_type = "MATERIAL"
    shading.show_cavity = False
    scene.render.resolution_x, scene.render.resolution_y = IMG_SIZE
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = False
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)

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
    if steps:
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
            render_case(obj, os.path.join(OUT_DIR, case["id"], "image.png"))
            entry["image"] = "image.png"
        except Exception as exc:  # noqa: BLE001
            entry["image"] = None
            entry["error"] = "render failed: %s" % exc
    else:
        entry["mesh"] = None
        entry["geometry_hash"] = None
        entry["validation"] = None
        entry["geometry_report"] = None
        entry["image"] = None

    import building_tools

    entry["environment"] = {
        "blender": bpy.app.version_string,
        "addon_version": ".".join(str(x) for x in building_tools.bl_info.get("version", ())),
    }
    return entry


def main():
    import importlib.util

    spec = importlib.util.spec_from_file_location("ref_cases", CASES_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    cases = mod.CASES

    if FILTER:
        import fnmatch
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
            "image": entry.get("image"),
        })
        print("[sweep] %d/%d %-32s %s" % (i + 1, len(cases), entry["id"], status))

    with open(os.path.join(OUT_DIR, "index.json"), "w") as f:
        json.dump({"image_size": list(IMG_SIZE), "cases": index}, f, indent=2, sort_keys=True)

    # -- human-browsable gallery
    lines = ["# Reference corpus", "",
             "image size: %dx%d -- %d cases" % (IMG_W, IMG_H, len(cases)), ""]
    for e in index:
        lines.append("## %s" % e["id"])
        lines.append("")
        lines.append("- status: `%s`" % e["status"])
        lines.append("- faces: %s -- geometry_hash: `%s`" % (e["faces"], e["geometry_hash"]))
        if e["problems"]:
            lines.append("- problems: %s (known: %s)" % (e["problems"], e["known_issues"]))
        if e["image"]:
            lines.append("")
            lines.append("![%s](%s/image.png)" % (e["id"], e["id"]))
        lines.append("")
    with open(os.path.join(OUT_DIR, "index.md"), "w") as f:
        f.write("\n".join(lines))

    print("__JSON__" + json.dumps({
        "generated": len(index),
        "out_dir": OUT_DIR,
        "failed": [e["id"] for e in index if e["status"] not in ("ok",)],
    }))


main()
