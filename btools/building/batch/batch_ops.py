import bpy

from .batch_props import BatchProperty


class BTOOLS_OT_batch_generate(bpy.types.Operator):
    """Generate buildings from selected footprint objects using their
    custom properties (roof shape, height, levels...)"""

    bl_idname = "btools.batch_generate"
    bl_label = "Batch Generate Buildings"
    bl_options = {"REGISTER", "UNDO"}

    props: bpy.props.PointerProperty(type=BatchProperty)

    @classmethod
    def poll(cls, context):
        return context.mode == "OBJECT" and any(
            o.type == "MESH" and o.select_get() for o in context.scene.objects
        )

    def execute(self, context):
        import dataclasses

        from ...api import batch_summary, generate_batch
        from ...api.options import BatchOptions

        selected = [
            o for o in context.scene.objects if o.select_get() and o.type == "MESH"
        ]
        kwargs = {
            f.name: getattr(self.props, f.name)
            for f in dataclasses.fields(BatchOptions)
        }
        options = BatchOptions(**kwargs)
        results = generate_batch(selected, options)
        text = batch_summary(results)
        for r in results:
            for w in r.warnings:
                self.report({"WARNING"}, "%s: %s" % (r.object_name, w))
        self.report({"INFO"}, text)
        return {"FINISHED"}

    def draw(self, context):
        self.props.draw(context, self.layout)

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=280)
