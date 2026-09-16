"""Slope by absolute height — the default slope mode."""
TAGS = ("slope-height", "roof-gable", "simple")
TIER = "simple"


def build(ctx):
    ctx.floorplan(type="RECTANGULAR", width=10.0, length=8.0)
    ctx.floors(floor_count=1, floor_height=3.0)
    ctx.roof(type="GABLE", height=1.8)
