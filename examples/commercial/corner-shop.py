"""Corner shop — glazed shopfront, flat roof, awning-style border"""

TAGS = ('fp-rect', 'roof-flat', 'multigroup', 'hardware', 'fill-glass', 'simple')
TIER = 'standard'


def build(ctx):
    def build(ctx):
        ctx.floorplan(type="RECTANGULAR", width=8.0, length=8.0)
        ctx.floors(floor_count=2, floor_height=3.5)
        ctx.roof(type="FLAT", add_border=True, border=0.2)
        ctx.doors(size_offset={"size": [4.0, 2.8]}, fill_type="GLASS_PANES")
