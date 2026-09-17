"""Church — nave with steep gable, arched windows, rose-style circular window"""

TAGS = ('fp-rect', 'roof-gable', 'window-arch', 'window-circle', 'showcase')
TIER = 'standard'


def build(ctx):
    ctx.floorplan(type="RECTANGULAR", width=9.0, length=18.0)
    ctx.floors(floor_count=1, floor_height=6.0)
    ctx.roof(type="GABLE", slope_mode="ANGLE", slope_angle=0.9)
    ctx.windows(fill_type="GLASS_PANES", add_arch=True)
    ctx.feature("window", "front_walls", type="CIRCULAR",
                size_offset={"size": [1.6, 1.6]})
