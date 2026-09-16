"""Car showroom — glass curtain walls, flat roof"""

TAGS = ('fp-rect', 'roof-flat', 'multigroup', 'fill-glass', 'standard')
TIER = 'standard'


def build(ctx):
    def build(ctx):
        ctx.floorplan(type="RECTANGULAR", width=16.0, length=10.0)
        ctx.floors(floor_count=1, floor_height=4.5)
        ctx.roof(type="FLAT", thickness=0.35)
        ctx.windows(fill_type="GLASS_PANES", size_offset={"size": [5.0, 3.2]})
