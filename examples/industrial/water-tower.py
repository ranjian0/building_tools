"""Water tower — tall circular shaft"""

TAGS = ('fp-circle', 'roof-hip', 'simple')
TIER = 'standard'


def build(ctx):
    ctx.floorplan(type="CIRCULAR", radius=2.2, segments=16)
    ctx.floors(floor_count=2, floor_height=6.0)
    ctx.roof(type="HIP", slope_mode="ANGLE", slope_angle=0.7)
