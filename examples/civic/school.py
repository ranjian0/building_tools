"""School — 2 storeys, uniform window rows, flat roof"""

TAGS = ('fp-rect', 'roof-flat', 'windows', 'simple')
TIER = 'standard'


def build(ctx):
    def build(ctx):
        ctx.floorplan(type="RECTANGULAR", width=24.0, length=12.0)
        ctx.floors(floor_count=2, floor_height=3.4)
        ctx.roof(type="FLAT", add_border=True)
        ctx.windows(storeys=(0, 1), array={"count": 7})
