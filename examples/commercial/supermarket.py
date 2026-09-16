"""Supermarket — wide flat box, parapet, minimal openings"""

TAGS = ('fp-rect', 'roof-flat', 'simple')
TIER = 'standard'


def build(ctx):
    def build(ctx):
        ctx.floorplan(type="RECTANGULAR", width=28.0, length=18.0)
        ctx.floors(floor_count=1, floor_height=6.0)
        ctx.roof(type="FLAT", thickness=0.4, add_border=True, border=0.4)
