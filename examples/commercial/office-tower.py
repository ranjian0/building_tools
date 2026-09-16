"""Office tower — 14 storeys, half-hip crown"""

TAGS = ('fp-rect', 'roof-halfhip', 'windows', 'standard')
TIER = 'standard'


def build(ctx):
    def build(ctx):
        ctx.floorplan(type="RECTANGULAR", width=14.0, length=14.0)
        ctx.floors(floor_count=14, floor_height=3.1)
        ctx.roof(type="HALF_HIP", height=3.0, ridge_fraction=0.7)
        ctx.windows(storeys=tuple(range(1, 14)), array={"count": 5},
                    fill_type="GLASS_PANES")
