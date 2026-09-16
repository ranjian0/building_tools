"""Workshop — flat-top roof with overhang, roller-style door"""

TAGS = ('fp-rect', 'roof-flattop', 'simple')
TIER = 'standard'


def build(ctx):
    def build(ctx):
        ctx.floorplan(type="RECTANGULAR", width=12.0, length=9.0)
        ctx.floors(floor_count=1, floor_height=4.0)
        ctx.roof(type="FLAT_TOP", slope_mode="ANGLE", slope_angle=0.7,
                 flat_height=1.0, outset=0.4)
        ctx.doors(size_offset={"size": [3.0, 3.2]})
