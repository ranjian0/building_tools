"""Random floorplan — seeded procedural plan with fixed wing count."""
TAGS = ("fp-random", "seed", "simple")
TIER = "simple"


def build(ctx):
    ctx.floorplan(type="RANDOM", seed=7, extension_amount=3,
                  random_extension_amount=False, width=12.0, length=9.0)
    ctx.floors(floor_count=1, floor_height=3.0)
