"""Grain silo — circular footprint, flat-top cap"""

TAGS = ('fp-circle', 'roof-flattop', 'simple')
TIER = 'standard'


def build(ctx):
    def build(ctx):
        ctx.floorplan(type="CIRCULAR", radius=3.0, segments=24)
        ctx.floors(floor_count=1, floor_height=8.0)
        ctx.roof(type="FLAT_TOP", slope_mode="ANGLE", slope_angle=0.9,
                 flat_height=0.6, outset=0.3)
