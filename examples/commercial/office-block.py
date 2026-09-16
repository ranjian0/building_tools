"""Office block — 6 storeys, curtain-wall window grid, flat roof"""

TAGS = ('fp-rect', 'roof-flat', 'windows', 'standard')
TIER = 'standard'


def build(ctx):
    def build(ctx):
        ctx.floorplan(type="RECTANGULAR", width=18.0, length=12.0)
        ctx.floors(floor_count=6, floor_height=3.2)
        ctx.roof(type="FLAT", add_border=True)
        ctx.windows(storeys=tuple(range(6)), array={"count": 6},
                    fill_type="GLASS_PANES")
