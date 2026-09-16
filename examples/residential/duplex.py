"""Duplex — two mirrored units under a half-hip roof"""

TAGS = ('fp-rect', 'roof-halfhip', 'windows', 'doors', 'standard')
TIER = 'standard'


def build(ctx):
    def build(ctx):
        ctx.floorplan(type="RECTANGULAR", width=12.0, length=9.0)
        ctx.floors(floor_count=2, floor_height=3.0)
        ctx.roof(type="HALF_HIP", height=2.2, ridge_fraction=0.6)
        ctx.doors(array={"count": 2})
        ctx.windows(storeys=(1,), fill_type="GLASS_PANES")
