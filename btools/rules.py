"""Rule-file context: the vocabulary rule files use (roadmap phase 3).

A rule file is plain Python with an optional ``build(ctx) -> str | None``
entry point; module-level scripts also work (the context is injected
before execution). The context wraps the scriptable api with the three
building steps (floorplan / floors / roof), interior partitions, window
placement and the confirmation channels (ascii / render / export)::

    def build(ctx):
        ctx.floorplan(type="RECTANGULAR", width=10, length=8)
        ctx.floors(floor_count=2, floor_height=3.0, wall_thickness=0.25)
        ctx.roof(type="GABLE", height=1.8, add_gutters=True)
        ctx.interior(mode="TREEMAP", room_count=5, inset=0.25)
        ctx.windows(storeys=(1,), fill_type="GLASS_PANES")
        ctx.render("confirm.png", views=("front", "iso"))
        ctx.export("house.glb")
"""

from .api import probe
from .api.core import FaceTarget, options_from_dict
from .api.select import select
from .render import render as _render
from .render import render_views as _render_views


class RuleContext:
    """The object handed to ``build(ctx)`` in rule files."""

    def __init__(self, options=None):
        import bpy

        from . import ensure_registered

        ensure_registered()
        self._bpy = bpy
        self._options = options
        self.objects = []  # created object names, in order
        self.results = []  # every OpResult, in order
        self.decisions = []  # seeded-rng decision log
        self.warnings = []

    # ---------------------------------------------------------------- tracking

    def _record(self, res, name=None):
        self.results.append(res)
        self.warnings.extend(res.warnings)
        self.decisions.extend(res.decisions)
        if name:
            self.objects.append(name)
        elif res.created_object:
            self.objects.append(res.created_object)
        return res

    @property
    def object(self):
        """The most recently created object name (or None)."""
        return self.objects[-1] if self.objects else None

    def object_data(self, name=None):
        import bpy

        return bpy.data.objects.get(name or self.object)

    def log(self, *messages):
        print("[btools]", *messages)

    # ---------------------------------------------------------------- steps

    def floorplan(self, **opts):
        res = self._apply("floorplan", opts)
        self._record(res)
        return res

    def floors(self, **opts):
        obj = self.object_data()
        res = self._apply("floor", opts, FaceTarget(obj))
        self._record(res)
        return res

    def roof(self, target=None, **opts):
        obj = self.object_data()
        top = select(obj, "top_face")
        if not top:
            from .api.result import OpResult

            res = OpResult("cancelled", "roof", errors=["no top face"])
        else:
            res = self._apply("roof", opts, FaceTarget(obj, top))
        self._record(res)
        return res

    def interior(self, **opts):
        return self.partitions(**opts)

    def partitions(self, **opts):
        obj = self.object_data()
        face = _ground_floor_face(obj)
        if face is None:
            from .api.result import OpResult

            res = OpResult("cancelled", "interior", errors=["no floor face"])
        else:
            res = self._apply("interior", opts, FaceTarget(obj, [face]))
        self._record(res)
        return res

    def windows(self, storeys=None, **opts):
        """Place windows on wall faces (all storeys by default)."""
        obj = self.object_data()
        res = self._apply(
            "window", opts, FaceTarget(obj, select(obj, "walls", storeys=storeys))
        )
        self._record(res)
        return res

    def doors(self, **opts):
        obj = self.object_data()
        res = self._apply("door", opts, FaceTarget(obj, select(obj, "walls")))
        self._record(res)
        return res

    def _apply(self, name, opts, target=None):
        from .api.core import apply_feature, options_from_dict
        from .api.presets import PRESETS  # noqa: F401 -- keeps presets imported

        opt_cls = _option_types()[name]
        options = options_from_dict(opt_cls, opts) if opts else opt_cls()
        return apply_feature(name, options, target)

    def feature(self, name, face_selector=None, **opts):
        """Generic feature application."""
        if face_selector is None:
            res = self._apply(name, opts)
        else:
            obj = self.object_data()
            faces = (
                select(obj, face_selector)
                if isinstance(face_selector, str)
                else list(face_selector)
            )
            res = self._apply(name, opts, FaceTarget(obj, faces))
        self._record(res)
        return res

    def preset(self, preset, **kw):
        """Build a bundled preset by id (or pass a BuildingPreset)."""
        from .api.presets import PRESETS, build_preset

        if isinstance(preset, str):
            preset = PRESETS[preset]
        res = build_preset(preset, **kw)
        self._record(res, name=res.created_object)
        return res

    def batch(self, objects, **opts):
        from .api import BatchOptions
        from .api.batch import generate_batch as _generate

        opts = {"window_density": opts.pop("window_density", 0.0), **opts}
        batch_opts = options_from_dict(BatchOptions, opts)
        results = _generate(objects, batch_opts)
        self.results.extend(results)
        for r in results:
            self.warnings.extend(r.warnings)
            if r.created_object:
                self.objects.append(r.created_object)
        return results

    # ------------------------------------------------------------ rng / probes

    def rng(self, *path):
        from .utils.randomizer import BToolsRandom

        return BToolsRandom("rule").rng(*path)

    def ascii(self, view="front"):
        obj = self.object_data()
        if obj is None:
            return "(no object)"
        return probe.ascii_elevation(obj, view)

    def export(self, path, export_format=None, semantic_slots=True):
        from .building.export import export_object

        obj = self.object_data()
        ok, out, error = export_object(
            obj,
            filepath=path,
            export_format=export_format,
            semantic_slots=semantic_slots,
        )
        if not ok:
            self.warnings.append("export failed: %s" % error)
        return ok, out

    def render(
        self, path, engine=None, view="iso", views=None, resolution=(1280, 1280)
    ):
        """Render confirmation image(s). views=(...) renders a multi-view set."""
        if views:
            return _render_views(
                path, views=views, engine=engine, resolution=resolution
            )
        _, path = _render(path, engine=engine, view=view, resolution=resolution)
        return path


def _option_types():
    from .api.core import OPTION_TYPES

    return OPTION_TYPES


def _ground_floor_face(obj):
    """Largest upward-facing slab-group face near the ground."""

    me = obj.data
    names = [mt.name for mt in getattr(obj, "bt_materials", [])]
    layer = me.attributes.get(".bt_material_group_index")
    if layer is None or "slabs" not in names:
        return None
    slab_idx = names.index("slabs")
    vals = [0] * len(me.polygons)
    layer.data.foreach_get("value", vals)
    best, best_area = None, 0.0
    for i, (poly, tag) in enumerate(zip(me.polygons, vals)):
        if tag != slab_idx:
            continue
        center = poly.center
        if center.z > 0.6:
            continue
        if poly.area > best_area:
            best, best_area = i, poly.area
    return best
