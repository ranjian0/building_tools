"""Modern villa — flat roof, ribbon glazing, thin slab lines"""

TAGS = ('fp-rect', 'roof-flat', 'windows', 'simple')
TIER = 'standard'


def build(ctx):
    def build(ctx):
        ctx.floorplan(type="RECTANGULAR", width=14.0, length=10.0)
        ctx.floors(floor_count=2, floor_height=3.2, add_slab=True)
        ctx.roof(type="FLAT", thickness=0.25, outset=0.4, add_border=True)
        ctx.windows(fill_type="GLASS_PANES", size_offset={"size": [2.4, 1.8]})
