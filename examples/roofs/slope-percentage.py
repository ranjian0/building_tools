"""Slope by percentage — 100 percent equals a 45-degree pitch."""
TAGS = ("slope-percentage", "roof-gable", "simple")
TIER = "simple"


def build(ctx):
    ctx.floorplan(type="RECTANGULAR", width=10.0, length=8.0)
    ctx.floors(floor_count=1, floor_height=3.0)
    ctx.roof(type="GABLE", slope_mode="PERCENTAGE", slope_percentage=100.0)
