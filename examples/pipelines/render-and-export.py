"""Render-and-export — build, confirm with multi-view renders, ship a glb."""
TAGS = ("pipeline", "render", "export", "seed")


def build(ctx):
    import os
    import tempfile

    ctx.floorplan(type="RECTANGULAR", width=10.0, length=8.0)
    ctx.floors(floor_count=2, floor_height=3.0)
    ctx.roof(type="HIP", height=1.8)
    # two confirmation views + a production glb (use a real out dir)
    out = tempfile.mkdtemp(prefix="btools-demo-")
    ctx.render(os.path.join(out, "confirm.png"), views=("front", "iso"))
    ctx.export(os.path.join(out, "house.glb"))
    print("outputs in", out)
