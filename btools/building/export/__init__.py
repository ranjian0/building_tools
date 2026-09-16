"""Production export of generated buildings (glTF / FBX).

The matgroup face layer is the semantic source: every face carries a
material slot named after its group (BT_walls, BT_roof, BT_door, ...),
so imported assets arrive with named material slots ready for engine
materials. Exports work on a temporary duplicate with transforms
applied -- the scene object is never modified.
"""

import os

import bpy
from bpy.props import BoolProperty, EnumProperty, StringProperty

_FORMATS = (
    ("GLB", "glTF Binary (.glb)", "Binary glTF: best for game engines"),
    ("FBX", "FBX (.fbx)", "FBX: best for DCC interop"),
)

_EXTENSIONS = {"GLB": ".glb", "FBX": ".fbx"}


def prepare_export_object(obj, semantic_slots=True, name_suffix=""):
    """Duplicate `obj` with transforms applied and (optionally) material
    slots rebuilt from the matgroup layer. Returns the duplicate (linked
    to the current collection, selected and active)."""
    dup = obj.copy()
    dup.data = obj.data.copy()
    dup.name = obj.name + name_suffix
    bpy.context.scene.collection.objects.link(dup)

    if semantic_slots:
        from ..default_materials import apply_default_materials

        apply_default_materials(dup, untagged=False)

    # -- isolate selection and apply transforms so the exported asset is
    #    oriented/scaled the way it appears
    for o in bpy.context.view_layer.objects:
        o.select_set(o == dup)
    bpy.context.view_layer.objects.active = dup
    if dup.rotation_mode != "QUATERNION":
        dup.rotation_mode = "QUATERNION"
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    return dup


def _default_directory():
    blend = bpy.path.abspath("//")
    if blend and os.path.isdir(blend):
        out = os.path.join(blend, "buildings")
        os.makedirs(out, exist_ok=True)
        return out
    import tempfile

    return tempfile.gettempdir()


def export_object(obj, filepath=None, export_format=None, semantic_slots=True):
    """Export one object as a production asset. Returns (ok, path, error).

    export_format None infers GLB/FBX from the filepath extension."""
    if export_format is None:
        ext = os.path.splitext(filepath or "")[1].lower().lstrip(".")
        export_format = {"glb": "GLB", "fbx": "FBX"}.get(ext)
        if export_format is None and filepath:
            return False, filepath, "cannot infer format from %r" % filepath
    if export_format not in _EXTENSIONS:
        return False, None, "unknown format %r" % export_format
    if filepath is None:
        filepath = os.path.join(
            _default_directory(), obj.name + _EXTENSIONS[export_format]
        )
    filepath = os.path.abspath(filepath)

    dup = prepare_export_object(obj, semantic_slots=semantic_slots)
    try:
        if export_format == "GLB":
            bpy.ops.export_scene.gltf(
                filepath=filepath,
                export_format="GLB",
                use_selection=True,
                export_apply=False,  # transforms already applied
                export_yup=True,
            )
        else:
            bpy.ops.export_scene.fbx(
                filepath=filepath,
                use_selection=True,
                apply_unit_scale=True,
                apply_scale_options="FBX_SCALE_ALL",
                object_types={"MESH"},
                use_mesh_modifiers=True,
            )
    except RuntimeError as exc:
        return False, filepath, str(exc)
    finally:
        bpy.data.objects.remove(dup, do_unlink=True)

    return (
        os.path.isfile(filepath),
        filepath,
        None if os.path.isfile(filepath) else "export produced no file",
    )


def semantic_slot_names(obj):
    """Material slot names an export would use for this object (preview)."""
    from ...api.validate import matgroup_report

    return sorted({"BT_" + name for name in matgroup_report(obj)["groups"]})


class BTOOLS_OT_export_building(bpy.types.Operator):
    """Export the active building as a production asset (glTF/FBX) with
    semantic material slots from material groups"""

    bl_idname = "btools.export_building"
    bl_label = "Export Building"
    bl_options = {"REGISTER"}

    export_format: EnumProperty(name="Format", items=_FORMATS, default="GLB")
    semantic_slots: BoolProperty(
        name="Semantic Slots",
        default=True,
        description="Rebuild material slots from material groups "
        "(BT_walls, BT_roof, ...) before exporting",
    )
    filepath: StringProperty(subtype="FILE_PATH")

    @classmethod
    def poll(cls, context):
        return (
            context.object is not None
            and context.object.type == "MESH"
            and context.mode == "OBJECT"
        )

    def execute(self, context):
        ok, path, error = export_object(
            context.object,
            filepath=bpy.path.abspath(self.filepath) if self.filepath else None,
            export_format=self.export_format,
            semantic_slots=self.semantic_slots,
        )
        if not ok:
            self.report({"ERROR"}, "export failed: %s" % (error or "unknown"))
            return {"CANCELLED"}
        self.report({"INFO"}, "exported %s" % path)
        return {"FINISHED"}

    def invoke(self, context, event):
        self.filepath = os.path.join(
            _default_directory(),
            context.object.name + _EXTENSIONS[self.export_format],
        )
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "export_format", expand=True)
        layout.prop(self, "semantic_slots")


def register():
    bpy.utils.register_class(BTOOLS_OT_export_building)


def unregister():
    bpy.utils.unregister_class(BTOOLS_OT_export_building)
