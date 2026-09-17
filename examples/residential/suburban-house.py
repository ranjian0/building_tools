"""Suburban house — 2 storeys, open gable, gutters and chimney"""

TAGS = ('fp-rect', 'roof-gable', 'gutters', 'chimney', 'ridge-cap', 'windows', 'fill-panels', 'simple')
TIER = 'standard'


def build(ctx):
    ctx.floorplan(type="RECTANGULAR", width=10.0, length=8.0)
    ctx.floors(floor_count=2, floor_height=3.0)
    ctx.roof(type="GABLE", height=1.8, add_gutters=True, add_chimney=True)
    ctx.windows(storeys=(0, 1), fill_type="GLASS_PANES")
