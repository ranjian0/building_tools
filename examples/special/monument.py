"""Monument — solid flat-top block, no openings"""

TAGS = ('fp-rect', 'roof-flattop', 'simple')
TIER = 'standard'


def build(ctx):
    def build(ctx):
        ctx.floorplan(type="RECTANGULAR", width=6.0, length=6.0)
        ctx.floors(floor_count=1, floor_height=7.0)
        ctx.roof(type="FLAT_TOP", slope_mode="ANGLE", slope_angle=0.8,
                 flat_height=1.0, outset=0.4)
