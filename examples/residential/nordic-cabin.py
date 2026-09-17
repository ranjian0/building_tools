"""Nordic cabin — small footprint, steep hip roof, deep roof outset"""

TAGS = ('fp-rect', 'roof-hip', 'simple')
TIER = 'standard'


def build(ctx):
    ctx.floorplan(type="RECTANGULAR", width=6.0, length=5.0)
    ctx.floors(floor_count=1, floor_height=2.8)
    ctx.roof(type="HIP", slope_mode="ANGLE", slope_angle=0.8727, outset=0.5)
