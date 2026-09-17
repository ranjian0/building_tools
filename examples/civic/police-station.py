"""Police station — office-style 2-storey block"""

TAGS = ('fp-rect', 'roof-flat', 'windows', 'simple')
TIER = 'standard'


def build(ctx):
    ctx.floorplan(type="RECTANGULAR", width=14.0, length=10.0)
    ctx.floors(floor_count=2, floor_height=3.2)
    ctx.roof(type="FLAT", add_border=True, border=0.25)
    ctx.windows(storeys=(1,), array={"count": 4})
