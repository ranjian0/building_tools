"""Circular floorplan — low segment count for a faceted drum look."""
TAGS = ("fp-circle", "segments", "simple")
TIER = "simple"


def build(ctx):
    ctx.floorplan(type="CIRCULAR", radius=4.0, segments=8)
    ctx.floors(floor_count=1, floor_height=3.5)
