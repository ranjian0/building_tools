"""Rectangular floorplan — the simplest starting point."""
TAGS = ("fp-rect", "simple")
TIER = "simple"


def build(ctx):
    ctx.floorplan(type="RECTANGULAR", width=10.0, length=8.0)
    ctx.floors(floor_count=1, floor_height=3.0)
