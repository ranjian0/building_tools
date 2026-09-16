"""OSM batch block — eight footprints with Simple-3D-Buildings attributes."""
TAGS = ("pipeline", "batch", "seed")


def build(ctx):
    import bpy

    specs = [
        ("shop",     {"roof:shape": "flat", "building:levels": 1}),
        ("house_a",  {"roof:shape": "gabled", "roof:angle": 40.0, "building:levels": 2}),
        ("house_b",  {"roof:shape": "half-hipped", "building:levels": 2}),
        ("terrace",  {"roof:shape": "pitched", "height": 7.0}),
        ("walkup",   {"roof:shape": "hipped", "building:levels": 3}),
        ("block",    {"roof:shape": "flat", "height": 12.0}),
        ("silo",     {"roof:shape": "cone", "height": 10.0}),
        ("shed",     {"roof:shape": "shed", "building:levels": 1}),
    ]
    import bmesh

    for i, (name, attrs) in enumerate(specs):
        me = bpy.data.meshes.new(name)
        obj = bpy.data.objects.new(name, me)
        bpy.context.scene.collection.objects.link(obj)
        bm = bmesh.new()
        vs = [
            bm.verts.new((i * 14.0 - 7.0 + dx, dy, 0.0))
            for dx, dy in [(-4, -3), (4, -3), (4, 3), (-4, 3)]
        ]
        bm.faces.new(vs)
        bm.normal_update()
        bm.to_mesh(me)
        bm.free()
        for k, v in attrs.items():
            obj[k] = v

    ctx.batch(
        [o for o in bpy.data.objects if not o.name.endswith("_bld")],
        window_density=0.5,
    )
