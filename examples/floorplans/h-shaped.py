"""H-shaped floorplan — twin wings with parameterised link thickness."""
TAGS = ("fp-h", "simple")
TIER = "simple"


def build(ctx):
    ctx.floorplan(type="H-SHAPED", width=14.0, length=12.0)
    ctx.floors(floor_count=1, floor_height=3.0)
