"""Modern museum — flat-top roof, minimal openings, wide cantilever"""

TAGS = ('fp-rect', 'roof-flattop', 'simple')
TIER = 'standard'


def build(ctx):
    def build(ctx):
        ctx.floorplan(type="RECTANGULAR", width=18.0, length=14.0)
        ctx.floors(floor_count=1, floor_height=5.0)
        ctx.roof(type="FLAT_TOP", slope_mode="ANGLE", slope_angle=0.6,
                 flat_height=0.9, outset=0.6)
