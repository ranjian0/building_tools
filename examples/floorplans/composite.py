"""Composite floorplan — four wing-width/thickness parameters."""
TAGS = ("fp-composite", "simple")
TIER = "simple"


def build(ctx):
    ctx.floorplan(type="COMPOSITE", width=16.0, length=12.0,
                  tw1=1.0, tw2=1.5, tw3=1.0, tl1=2.0, tl2=2.0,
                  tl3=2.0, tl4=2.0)
    ctx.floors(floor_count=1, floor_height=3.0)
