"""Bell tower — slender square shaft with an open crown"""

TAGS = ('fp-rect', 'roof-flattop', 'simple')
TIER = 'standard'


def build(ctx):
    def build(ctx):
        ctx.floorplan(type="RECTANGULAR", width=4.0, length=4.0)
        ctx.floors(floor_count=1, floor_height=9.0)
        ctx.roof(type="FLAT_TOP", height=2.0, flat_height=1.5, outset=0.35)
