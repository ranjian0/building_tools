"""High-rise tower — 12 storeys, uniform window grid, flat roof"""

TAGS = ('fp-rect', 'roof-flat', 'windows', 'standard')
TIER = 'standard'


def build(ctx):
    ctx.floorplan(type="RECTANGULAR", width=14.0, length=14.0)
    ctx.floors(floor_count=12, floor_height=3.0)
    ctx.roof(type="FLAT", thickness=0.4, outset=0.3)
    ctx.windows(storeys=tuple(range(1, 12)), array={"count": 5},
                fill_type="GLASS_PANES")
