"""Lighthouse — tall circular shaft, gallery roof"""

TAGS = ('fp-circle', 'roof-flattop', 'simple')
TIER = 'standard'


def build(ctx):
    def build(ctx):
        ctx.floorplan(type="CIRCULAR", radius=2.0, segments=20)
        ctx.floors(floor_count=1, floor_height=12.0)
        ctx.roof(type="FLAT_TOP", slope_mode="ANGLE", slope_angle=0.9,
                 flat_height=0.8, outset=0.5)
        ctx.windows(storeys=(0,), size_offset={"size": [0.5, 0.8]})
