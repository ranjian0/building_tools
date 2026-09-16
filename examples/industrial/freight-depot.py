"""Freight depot — long flat box, louvered vents, roller doors"""

TAGS = ('fp-rect', 'roof-flat', 'window-louver', 'standard')
TIER = 'standard'


def build(ctx):
    def build(ctx):
        ctx.floorplan(type="RECTANGULAR", width=24.0, length=12.0)
        ctx.floors(floor_count=1, floor_height=5.0)
        ctx.roof(type="FLAT")
        ctx.windows(fill_type="LOUVER", size_offset={"size": [1.2, 1.0]},
                    array={"count": 8})
