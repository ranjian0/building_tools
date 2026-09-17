"""Student housing — long uniform block, louvered window fills"""

TAGS = ('fp-rect', 'roof-flat', 'window-louver', 'simple')
TIER = 'standard'


def build(ctx):
    ctx.floorplan(type="RECTANGULAR", width=22.0, length=10.0)
    ctx.floors(floor_count=4, floor_height=2.8)
    ctx.roof(type="FLAT")
    ctx.windows(storeys=(1, 2, 3), array={"count": 8}, fill_type="LOUVER")
