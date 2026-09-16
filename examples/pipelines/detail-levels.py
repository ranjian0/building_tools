"""Detail levels — the same house at LOW and MEDIUM detail."""
TAGS = ("pipeline", "detail-level", "gutters", "chimney")


def build(ctx):
    for level in ("LOW", "MEDIUM"):
        ctx.detail(level)
        ctx.floorplan(type="RECTANGULAR", width=10.0, length=8.0)
        ctx.floors(floor_count=2, floor_height=3.0)
        ctx.roof(type="GABLE", height=1.8, add_gutters=True, add_chimney=True)
