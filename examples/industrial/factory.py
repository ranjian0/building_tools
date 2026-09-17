"""Factory — large flat footprint, parapet, strip windows"""

TAGS = ('fp-rect', 'roof-flat', 'windows', 'simple')
TIER = 'standard'


def build(ctx):
    ctx.floorplan(type="RECTANGULAR", width=30.0, length=20.0)
    ctx.floors(floor_count=1, floor_height=7.0)
    ctx.roof(type="FLAT", thickness=0.5, add_border=True, border=0.5)
    ctx.windows(fill_type="GLASS_PANES", size_offset={"size": [2.0, 1.2]},
                array={"count": 10})
